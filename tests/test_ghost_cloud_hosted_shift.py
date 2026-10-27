"""Offline tests: GitHub runner must never silently bypass the private Site."""
import contextlib
import io
import json
import os
import socket
import ssl
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import ghost_cloud_hosted_shift as runner

TOKEN = "owner-private-test-token-" + "x" * 40


class Reply:
    def __init__(self, obj=None, content=None, status=200):
        self.body = json.dumps(obj).encode() if content is None else content
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, max_bytes):
        return self.body[:max_bytes]


class Client:
    def __init__(self, reply):
        self.reply = reply
        self.request = None

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return self.reply


def receipt(enabled=True, dispatched=1, queued=0, denied=None):
    return {
        "intake": {"queued": queued, "duplicates": 0},
        "result": {"enabled": enabled, "dispatched": dispatched,
                   "denied": denied if denied is not None else {"gemini": "not_configured"}},
        "observed_at": 1234567890000,
    }


class HostedShiftTests(unittest.TestCase):
    def test_one_post_to_pinned_private_service_only(self):
        client = Client(Reply(receipt(dispatched=1, queued=2)))
        result = runner.send_shift(token=TOKEN, opener=client)
        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["newly_admitted_approved_jobs"], 2)
        self.assertEqual(result["admission_denied_provider_count"], 1)
        self.assertEqual(client.request.full_url, runner.TARGET)
        self.assertEqual(client.request.get_method(), "POST")
        self.assertEqual(client.request.data, b'{"operation":"shift"}')
        self.assertEqual(client.request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertEqual(client.timeout, 90)

    def test_no_arbitrary_target_or_short_service_secret(self):
        with self.assertRaisesRegex(ValueError, "unapproved_target"):
            runner.send_shift(token=TOKEN, url="https://evil.example/api/ghost/service")
        with self.assertRaisesRegex(ValueError, "service_secret_missing_or_short"):
            runner.send_shift(token="123", opener=Client(Reply(receipt())))

    def test_owner_stop_is_reported_as_paused(self):
        result = runner.send_shift(
            token=TOKEN, opener=Client(Reply(receipt(enabled=False, dispatched=0))))
        self.assertEqual(result["state"], "owner_paused")
        self.assertEqual(result["dispatched"], 0)

    def test_invalid_receipts_rejected_without_inventing_execution(self):
        for body in [[], {}, {"intake": {"queued": 0}, "result": {"enabled": True}},
                     receipt(dispatched=True), receipt(dispatched=10),
                     receipt(dispatched=-1), receipt(queued=10),
                     receipt(enabled=False, dispatched=1)]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                runner.send_shift(token=TOKEN, opener=Client(Reply(body)))
        with self.assertRaisesRegex(ValueError, "response_too_large"):
            runner.send_shift(token=TOKEN, opener=Client(
                Reply(content=b"x" * (runner.MAX_BYTES + 1))))
        with self.assertRaisesRegex(ValueError, "non_json_receipt"):
            runner.send_shift(token=TOKEN, opener=Client(Reply(content=b"not-json")))

    def test_invalid_http_status_not_treated_as_shift(self):
        with self.assertRaisesRegex(ValueError, "unexpected_http_status"):
            runner.send_shift(token=TOKEN, opener=Client(Reply(receipt(), status=401)))

    def test_missing_action_secret_exits_visibly_without_inference(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"ROVOR_GHOST_SERVICE_TOKEN": "", "GITHUB_ACTIONS": "true"}):
            with patch.object(runner, "send_shift", side_effect=AssertionError("unexpected inference")):
                with contextlib.redirect_stdout(output):
                    code = runner.main()
        self.assertEqual(code, 2)
        lines = output.getvalue().splitlines()
        self.assertEqual(json.loads(lines[0])["state"], "not_armed")
        self.assertEqual(json.loads(lines[0])["dispatched"], 0)
        self.assertIn("::error title=ROVOR cloud scheduler not armed::", lines[1])
        self.assertNotIn(TOKEN, output.getvalue())

    def test_short_present_service_secret_fails_closed_before_any_network_call(self):
        output = io.StringIO()
        # GitHub masks populated secrets even when they fail the contract.
        short_secret = "present-but-short"
        with patch.dict(os.environ, {"ROVOR_GHOST_SERVICE_TOKEN": short_secret,
                                     "GITHUB_ACTIONS": "true"}):
            with patch.object(runner, "send_shift",
                              side_effect=AssertionError("must not dispatch")) as send:
                with contextlib.redirect_stdout(output):
                    code = runner.main()
        self.assertEqual(code, 2)
        send.assert_not_called()
        lines = output.getvalue().splitlines()
        self.assertEqual(json.loads(lines[0]),
                         {"state": "not_armed",
                          "reason": "repository_service_secret_too_short",
                          "dispatched": 0})
        self.assertIn("at least 32 characters", lines[1])
        self.assertNotIn(short_secret, output.getvalue())
        self.assertNotIn("must not dispatch", output.getvalue())

    def test_malformed_service_credential_is_rejected_before_any_request(self):
        for bad_token in ("x" * 32 + "\n", "x" * 32 + "\r",
                          "x" * 20 + " " + "x" * 20,
                          "x" * 32 + "é"):
            with self.subTest(category="header_format"), patch.dict(
                    os.environ, {"ROVOR_GHOST_SERVICE_TOKEN": bad_token,
                                 "GITHUB_ACTIONS": "true"}):
                output = io.StringIO()
                with patch.object(runner, "send_shift",
                                  side_effect=AssertionError("unexpected network")) as send:
                    with contextlib.redirect_stdout(output):
                        code = runner.main()
                self.assertEqual(code, 2)
                send.assert_not_called()
                self.assertEqual(json.loads(output.getvalue().splitlines()[0]),
                                 {"state": "not_armed",
                                  "reason": "repository_service_secret_invalid_bearer_format",
                                  "dispatched": 0})
                self.assertNotIn(bad_token, output.getvalue())
                with self.assertRaisesRegex(ValueError, "service_secret_invalid_bearer_format"):
                    runner.send_shift(token=bad_token, opener=Client(Reply(receipt())))

        # OS environment variables cannot contain NUL; assert direct API guard.
        with self.assertRaisesRegex(ValueError, "service_secret_invalid_bearer_format"):
            runner.send_shift(token="x" * 32 + "\x00",
                              opener=Client(Reply(receipt())))

    def test_32_character_service_secret_reaches_guarded_sender(self):
        token = "x" * 32
        with patch.dict(os.environ, {"ROVOR_GHOST_SERVICE_TOKEN": token}):
            with patch.object(runner, "send_shift",
                              return_value={"state": "executed", "dispatched": 0}) as send:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = runner.main()
        self.assertEqual(code, 0)
        send.assert_called_once_with(token=token)
        self.assertNotIn(token, output.getvalue())

    def test_safe_dispatch_failure_categories_are_visible_without_secrets(self):
        cases = [
            (urllib.error.URLError(socket.timeout("sensitive-token")), "private_service_timeout"),
            (urllib.error.URLError(ssl.SSLError("sensitive-token")), "private_service_tls_failure"),
            (urllib.error.URLError(OSError("sensitive-token")), "private_service_connection_failure"),
            (ValueError("non_json_receipt"), "non_json_receipt"),
            (ValueError("invalid_shift_receipt"), "invalid_shift_receipt"),
            (ValueError("sensitive-token"), "private_service_validation_failure"),
            (RuntimeError("sensitive-token"), "private_service_unknown_failure"),
        ]
        for raised, expected in cases:
            with self.subTest(reason=expected):
                output = io.StringIO()
                with patch.dict(os.environ, {"ROVOR_GHOST_SERVICE_TOKEN": TOKEN}):
                    with patch.object(runner, "send_shift", side_effect=raised):
                        with contextlib.redirect_stdout(output):
                            code = runner.main()
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(output.getvalue()),
                                 {"state": "dispatch_failed", "reason": expected})
                self.assertNotIn("sensitive-token", output.getvalue())
                self.assertNotIn(TOKEN, output.getvalue())

    def test_no_redirects_to_untrusted_origin(self):
        handler = runner.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "move", {},
                                                   "https://evil.example/"))

    def test_workflow_does_not_run_models_on_untrusted_pull_requests(self):
        workflow = (ROOT / ".github/workflows/ghost-cloud-github-scheduler.yml").read_text()
        self.assertIn("cron: '*/5 * * * *'", workflow)
        self.assertIn("github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("ROVOR_GHOST_SERVICE_TOKEN: " + chr(36) + "{{ secrets.ROVOR_GHOST_SERVICE_TOKEN }}", workflow)
        self.assertNotIn("pull_request_target", workflow)
        # Secret shape check may run on main pushes, but never on PRs.
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", workflow)
        self.assertIn("service-credential-preflight:", workflow)
        preflight = workflow.split("  service-credential-preflight:", 1)[1].split("\n  shift:", 1)[0]
        self.assertNotIn("actions/checkout", preflight)
        self.assertNotIn("tools/ghost_cloud_hosted_shift.py", preflight)
        self.assertIn("repository_service_secret_too_short", preflight)
        self.assertIn("repository_service_secret_invalid_bearer_format", preflight)
        self.assertIn("repository_service_secret_shape_ok", preflight)


if __name__ == "__main__":
    unittest.main()
