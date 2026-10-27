"""GitHub-hosted, fail-closed trigger for the EXISTING ROVOR private cloud dispatcher.

This is a scheduler, not an AI worker or an inference proxy. The private Site
alone decides STOP, owner-approved jobs, verified free eligibility, account
limits, pacing, durable claims and model responses. Never persist its secret.
"""
from __future__ import annotations

import json
import os
import re
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
    shift = result.get("shift")
    if not isinstance(shift, dict):
        raise ValueError("durable_shift_receipt_missing")
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

    # Require a durable shift receipt; a successful legacy tick is insufficient.
    shift_id = shift.get("id")
    shift_status = shift.get("status")
    if (not isinstance(shift_id, str)
            or not re.fullmatch(r"[a-z0-9-]{16,64}", shift_id)
            or shift_status not in {"dispatched", "idle", "stopped"}):
        raise ValueError("invalid_durable_shift_receipt")
    if (shift_status == "dispatched" and not (enabled and dispatched > 0)
            or shift_status == "idle" and not (enabled and dispatched == 0)
            or shift_status == "stopped" and not (enabled is False and dispatched == 0)):
        raise ValueError("inconsistent_durable_shift_receipt")
    # Public Actions logs must contain only allowlisted reason codes.
    reason = shift.get("reason")
    safe = {"no_unattempted_jobs", "no_eligible_providers",
            "unattempted_jobs_not_dispatched"}
    idle_reason = (reason if isinstance(reason, str) and reason in safe
                   else "claim_blocked" if isinstance(reason, str) and reason.startswith("claim_")
                   else "unknown")
    # Dispatch is a claimed attempt; it does not prove completion or 24/7 uptime.
    report = {
        "state": {"dispatched": "work_dispatched",
                  "idle": "idle_no_work",
                  "stopped": "owner_paused"}[shift_status],
        "dispatched": dispatched,
        "admission_denied_provider_count": len(denied),
        "newly_admitted_approved_jobs": queued,
        "source": "durable_private_cloud_shift_receipt",
    }
    if shift_status == "idle":
        report["idle_reason"] = idle_reason
    return report


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
    try:
        result = send_shift(token=token)
    except urllib.error.HTTPError as error:
        # No exception body; never follow auth redirects or echo private data.
        print(json.dumps({"state": "dispatch_failed", "http_status": error.code}))
        return 1
    except Exception:
        print(json.dumps({"state": "dispatch_failed", "reason": "private_service_unavailable_or_bad_receipt"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
