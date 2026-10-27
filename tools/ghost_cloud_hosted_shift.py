"""GitHub-hosted, fail-closed trigger for the EXISTING ROVOR private cloud dispatcher.

This is a scheduler, not an AI worker or an inference proxy. The private Site
alone decides STOP, owner-approved jobs, verified free eligibility, account
limits, pacing, durable claims and model responses. Never persist its secret.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request

TARGET = "https://rovor-private-hud.mm98z652cq.chatgpt.site/api/ghost/service"
MAX_BYTES = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def send_shift(*, token: str, url: str = TARGET, opener=None) -> dict:
    """Send exactly one shift request and return redacted *aggregate* evidence."""
    if url != TARGET:
        raise ValueError("unapproved_target")
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("service_secret_missing_or_short")

    request = urllib.request.Request(
        url,
        data=b'{"operation":"shift"}',
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    client = opener if opener is not None else urllib.request.build_opener(NoRedirect())
    with client.open(request, timeout=90) as response:
        if response.status != 200:
            raise ValueError("unexpected_http_status")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("response_too_large")

    try:
        result = json.loads(payload)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("non_json_receipt") from exc
    if not isinstance(result, dict):
        raise ValueError("invalid_shift_receipt")
    tick = result.get("result")
    intake = result.get("intake")
    if not isinstance(tick, dict) or not isinstance(intake, dict):
        raise ValueError("invalid_shift_receipt")

    enabled = tick.get("enabled")
    dispatched = tick.get("dispatched", 0 if enabled is False else None)
    denied = tick.get("denied", {})
    queued = intake.get("queued")
    if (not isinstance(enabled, bool)
            or type(dispatched) is not int or not 0 <= dispatched <= 9
            or not isinstance(denied, dict) or len(denied) > 9
            or type(queued) is not int or not 0 <= queued <= 9
            or (enabled is False and dispatched != 0)):
        raise ValueError("invalid_shift_receipt")

    # Keep all model IDs, prompts, job IDs, provider keys and private drafts out
    # of public Actions logs. "dispatched" is not proof of round-the-clock cron.
    return {
        "state": "executed" if enabled else "owner_paused",
        "dispatched": dispatched,
        "admission_denied_provider_count": len(denied),
        "newly_admitted_approved_jobs": queued,
        "source": "private_cloud_service_receipt",
    }


def main() -> int:
    token = os.environ.get("ROVOR_GHOST_SERVICE_TOKEN", "")
    if not token:
        print(json.dumps({
            "state": "not_armed",
            "reason": "repository_service_secret_not_configured",
            "dispatched": 0,
        }))
        # A green scheduled Actions run with zero credentials is misleading:
        # no Site call occurred and no cloud employees were dispatched.
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error title=ROVOR cloud scheduler not armed::Configure the ROVOR_GHOST_SERVICE_TOKEN Actions secret; zero cloud jobs were dispatched.")
        return 2
    if len(token) < 32:
        # This is a locally invalid GitHub Actions secret, not a Site outage.
        # Do not emit the value, length, hash, prefix, or any header data.
        print(json.dumps({
            "state": "not_armed",
            "reason": "repository_service_secret_too_short",
            "dispatched": 0,
        }))
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error title=ROVOR cloud scheduler credential invalid::Replace the matching GitHub Actions and private Site service credentials with one dedicated secret of at least 32 characters. Zero cloud jobs were dispatched.")
        return 2
    try:
        result = send_shift(token=token)
    except urllib.error.HTTPError as error:
        # No exception body; never follow auth redirects or echo private data.
        print(json.dumps({"state": "dispatch_failed", "http_status": error.code}))
        return 1
    except urllib.error.URLError as error:
        # The URL, server exception, TLS details and any credential are private.
        if isinstance(error.reason, (socket.timeout, TimeoutError)):
            reason = "private_service_timeout"
        elif isinstance(error.reason, ssl.SSLError):
            reason = "private_service_tls_failure"
        else:
            reason = "private_service_connection_failure"
        print(json.dumps({"state": "dispatch_failed", "reason": reason}))
        return 1
    except (socket.timeout, TimeoutError):
        print(json.dumps({"state": "dispatch_failed", "reason": "private_service_timeout"}))
        return 1
    except ValueError as error:
        # Whitelist only local parser codes. Never print arbitrary exception text.
        reason = str(error)
        if reason not in {
            "unexpected_http_status", "response_too_large",
            "non_json_receipt", "invalid_shift_receipt",
        }:
            reason = "private_service_validation_failure"
        print(json.dumps({"state": "dispatch_failed", "reason": reason}))
        return 1
    except Exception:
        print(json.dumps({"state": "dispatch_failed", "reason": "private_service_unknown_failure"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
