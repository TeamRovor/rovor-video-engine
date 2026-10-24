"""Offline tests for locally opted-in fixed macOS subprocess; no network or host execution."""
import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ghost_worker as worker
import ghost_private_control as control


class TerminalProbeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        (self.home / "Documents" / "Rovor").mkdir(parents=True)
        self.repo = "TeamRovor/rovor-mac-control"
        self.packet = {"schema": 1, "id": "terminal-probe-001",
                       "kind": "terminal.probe", "payload": {}}
        self.calls = []

    def http(self, method, path, token, body=None):
        self.assertEqual(token, "mock-token")
        self.calls.append((method, path, body))
        if method == "GET" and path == "/repos/" + self.repo:
            return {"full_name": self.repo, "private": True, "archived": False}
        if method == "GET" and path == "/repos/" + self.repo + "/contents/control/jobs/terminal-probe-001.json?ref=main":
            raw = json.dumps(self.packet).encode()
            return {"type": "file", "encoding": "base64", "size": len(raw),
                    "content": base64.b64encode(raw).decode()}
        if method == "POST" and path == "/repos/" + self.repo + "/issues/7/comments":
            return {"id": 42}
        self.fail("Unexpected GitHub request " + method + " " + path)

    def bridge(self, **kw):
        return control.bridge(self.repo, self.packet["id"], home=self.home,
                              token="mock-token", issue_number=7, http=self.http, **kw)

    def test_refuse_unapproved_terminal_and_remote_command_arguments(self):
        with self.assertRaises(control.Refused):
            self.bridge(execute=True)
        for payload in ({"shell": "sh"}, {"argv": ["/bin/ls"]},
                        {"command": "whoami"}, {"probe": "version"}):
            with self.subTest(payload=payload):
                self.packet["payload"] = payload
                with self.assertRaises(control.Refused):
                    self.bridge(allow_terminal_probe=True, execute=True)
        self.packet["payload"] = {}
        dry = self.bridge(allow_terminal_probe=True)
        self.assertEqual(dry["kind"], "terminal.probe")
        self.assertFalse(dry["executed"])
        self.assertFalse((self.home/"Documents"/"Rovor"/control.STATE).exists())
        self.assertFalse(any(m == "POST" for m, _, _ in self.calls))

    def test_normal_worker_refuses_to_claim_without_explicit_flag(self):
        state = self.home / "state"
        workspace = self.home / "workspace"
        workspace.mkdir()
        with worker.connect(state) as conn:
            worker.enqueue(conn, worker.TERMINAL_KIND, {}, "probe-unique")
            with mock.patch.object(worker, "macos_version_probe") as local_cmd:
                result = worker.run_once(conn, workspace)
            self.assertIsNone(result)
            local_cmd.assert_not_called()
            row = conn.execute("SELECT status,attempts FROM jobs").fetchone()
            self.assertEqual((row["status"], row["attempts"]), ("queued", 0))

    def test_exact_binary_and_bound_for_sanitized_result(self):
        captures = []
        def runner(cmd, **kw):
            captures.append((cmd, kw))
            return SimpleNamespace(returncode=0, stdout="15.7.3\n", stderr="DO NOT DISCLOSE")
        receipt = worker.macos_version_probe(run=runner, platform="darwin")
        self.assertEqual(receipt["macos_version"], "15.7.3")
        self.assertTrue(receipt["terminal_subprocess_verified"])
        self.assertEqual(captures[0][0], ["/usr/bin/sw_vers", "-productVersion"])
        self.assertEqual(captures[0][1]["timeout"], 8)
        self.assertEqual(captures[0][1]["cwd"], "/")
        self.assertEqual(captures[0][1]["env"], {"PATH": "/usr/bin:/bin"})
        self.assertFalse(captures[0][1]["check"])
        self.assertEqual(captures[0][1]["stdin"], subprocess.DEVNULL)

    def test_errors_invalid_outputs_and_non_mac_fail_closed(self):
        def result(txt, status=0):
            return lambda *a, **k: SimpleNamespace(returncode=status, stdout=txt, stderr="SECRET")
        with self.assertRaises(ValueError):
            worker.macos_version_probe(run=result("15.7"), platform="linux")
        for txt in ("15.7;echo leak", "a"*100, "15.7\n/private/path", "", "15.7.3.4"):
            with self.subTest(output=txt):
                with self.assertRaises(ValueError):
                    worker.macos_version_probe(run=result(txt), platform="darwin")
        with self.assertRaises(ValueError):
            worker.macos_version_probe(run=result("", 2), platform="darwin")
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("sw_vers", 8)
        with self.assertRaises(ValueError):
            worker.macos_version_probe(run=timeout, platform="darwin")

    def test_one_execution_sanitized_private_receipt_and_no_replay(self):
        proof = {"ok": True, "read_only": True, "command_id": "macos-version",
                 "macos_version": "26.1", "terminal_subprocess_verified": True}
        with mock.patch.object(worker, "macos_version_probe", return_value=proof) as spy:
            first = self.bridge(execute=True, allow_terminal_probe=True)
            again = self.bridge(execute=True, allow_terminal_probe=True)
        self.assertEqual(first["status"], "succeeded")
        self.assertTrue(first["executed"])
        self.assertFalse(again["executed"])
        spy.assert_called_once()
        posts = [data for method, _, data in self.calls if method == "POST"]
        self.assertEqual(len(posts), 1)
        receipt = json.loads(posts[0]["body"].split("ROVOR_PRIVATE_CONTROL_RECEIPT ", 1)[1])
        self.assertEqual(receipt["terminal_probe"],
                         {"command_id": "macos-version", "macos_version": "26.1"})
        self.assertTrue(receipt["terminal_subprocess_verified"])
        self.assertFalse(receipt["native_app_control_verified"])
        self.assertNotIn(str(self.home), json.dumps(receipt))
        self.assertNotIn("mock-token", json.dumps(receipt))

    def test_failure_needs_review_without_replay(self):
        with mock.patch.object(worker, "macos_version_probe", side_effect=ValueError("sensitive")) as spy:
            first = self.bridge(execute=True, allow_terminal_probe=True)
            again = self.bridge(execute=True, allow_terminal_probe=True)
        self.assertEqual(first["status"], "needs_review")
        self.assertFalse(again["executed"])
        spy.assert_called_once()
        self.assertNotIn("sensitive", json.dumps(self.calls))
        db = self.home/"Documents"/"Rovor"/control.STATE/self.packet["id"]/"jobs.sqlite3"
        with sqlite3.connect(str(db)) as conn:
            self.assertEqual(conn.execute("SELECT attempts FROM jobs").fetchone()[0], 1)

    def test_stop_blocks_every_command(self):
        state = self.home/"Documents"/"Rovor"/control.STATE
        state.mkdir()
        (state/"STOP").write_text("STOP")
        with mock.patch.object(worker, "macos_version_probe") as spy:
            report = self.bridge(execute=True, allow_terminal_probe=True)
        self.assertEqual(report["status"], "stopped")
        spy.assert_not_called()
        self.assertFalse(any(m == "POST" for m, _, _ in self.calls))


if __name__ == "__main__":
    unittest.main()
