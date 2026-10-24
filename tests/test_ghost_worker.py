"""Offline tests for the deliberately read-only ROVOR local worker prototype."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ghost_worker.py"
spec = importlib.util.spec_from_file_location("ghost_worker", SCRIPT)
ghost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ghost)


class GhostWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        self.state = base / "state"
        self.conn = ghost.connect(self.state)
        self.addCleanup(self.conn.close)

    def test_initializes_database(self):
        self.assertTrue((self.state / "jobs.sqlite3").exists())
        self.assertEqual(self.conn.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)

    def test_symlink_state_directory_rejected(self):
        redirect = Path(self.tmp.name) / "redirect"
        redirect.symlink_to(self.state, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            ghost.connect(redirect)

    def test_ping_job_succeeds(self):
        job = ghost.enqueue(self.conn, "system.ping", {}, "ping-1", now=100)
        result = ghost.run_once(self.conn, self.workspace, now=101)
        self.assertEqual(result["id"], job)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(json.loads(self.conn.execute("SELECT result FROM jobs WHERE id=?", (job,)).fetchone()[0])["ok"], True)

    def test_deduplication_is_stable(self):
        one = ghost.enqueue(self.conn, "system.ping", {}, "same", now=1)
        two = ghost.enqueue(self.conn, "system.ping", {}, "same", now=2)
        self.assertEqual(one, two)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
        with self.assertRaisesRegex(ValueError, "different work"):
            ghost.enqueue(self.conn, "files.inventory", {}, "same", now=3)

    def test_disabled_external_actions_fail_closed(self):
        for kind in ghost.FUTURE_DISABLED | {"shell.exec", "unknown"}:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "disabled"):
                ghost.enqueue(self.conn, kind, {}, kind)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)

    def test_file_inventory_does_not_read_contents(self):
        (self.workspace / "audio.mp3").write_bytes(b"secret-voice")
        d = self.workspace / "images"
        d.mkdir()
        (d / "logo.png").write_bytes(b"pixels")
        job = ghost.enqueue(self.conn, "files.inventory", {}, "inventory", now=1)
        result = ghost.run_once(self.conn, self.workspace, now=2)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["result"]["file_count"], 2)
        self.assertEqual([x["path"] for x in result["result"]["files"]], ["audio.mp3", "images/logo.png"])
        self.assertNotIn("secret-voice", json.dumps(result))
        self.assertTrue((self.workspace / "audio.mp3").exists())

    def test_inventory_traversal_is_rejected(self):
        job = ghost.enqueue(self.conn, "files.inventory", {"subpath": "../"}, "bad", now=1)
        result = ghost.run_once(self.conn, self.workspace, now=2)
        self.assertEqual(result["id"], job)
        self.assertEqual(result["status"], "failed")
        self.assertIn("escapes", result["error"])

    def test_symlink_escape_is_rejected(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "sensitive.txt").write_text("secret")
        (self.workspace / "link").symlink_to(outside, target_is_directory=True)
        x = ghost.inventory(self.workspace, ".")
        self.assertEqual(x["file_count"], 0)
        job = ghost.enqueue(self.conn, "files.inventory", {"subpath": "link"}, "link", now=1)
        self.assertEqual(ghost.run_once(self.conn, self.workspace, now=2)["status"], "failed")

    def test_running_lease_not_stolen_until_expired(self):
        ghost.enqueue(self.conn, "system.ping", {}, "lease", now=1)
        self.assertIsNotNone(ghost.claim(self.conn, "a", now=10))
        self.assertIsNone(ghost.claim(self.conn, "b", now=11))
        self.assertIsNotNone(ghost.claim(self.conn, "b", now=131))
        self.assertEqual(self.conn.execute("SELECT attempts FROM jobs").fetchone()[0], 2)

    def test_exhausted_lease_requires_review(self):
        ghost.enqueue(self.conn, "system.ping", {}, "lease", now=1)
        ghost.claim(self.conn, "a", now=10)
        ghost.claim(self.conn, "b", now=131)
        self.assertIsNone(ghost.claim(self.conn, "c", now=252))
        self.assertEqual(self.conn.execute("SELECT status FROM jobs").fetchone()[0], "needs_review")

    def test_receipt_and_events_persist_across_restart(self):
        job = ghost.enqueue(self.conn, "system.ping", {}, "restart", now=1)
        self.conn.close()
        self.conn = ghost.connect(self.state)
        self.assertEqual(ghost.run_once(self.conn, self.workspace, now=2)["status"], "succeeded")
        self.conn.close()
        self.conn = ghost.connect(self.state)
        status = self.conn.execute("SELECT status,result FROM jobs WHERE id=?", (job,)).fetchone()
        self.assertEqual(status["status"], "succeeded")
        self.assertTrue(json.loads(status["result"])["ok"])
        events = [r[0] for r in self.conn.execute("SELECT event FROM events WHERE job_id=? ORDER BY id", (job,))]
        self.assertEqual(events, ["submitted", "claimed", "succeeded"])

    def test_invalid_payload_or_keys_rejected(self):
        with self.assertRaises(ValueError):
            ghost.enqueue(self.conn, "files.inventory", {"delete": True}, "bad")
        with self.assertRaises(ValueError):
            ghost.enqueue(self.conn, "files.inventory", {"subpath": 123}, "bad")
        with self.assertRaises(ValueError):
            ghost.enqueue(self.conn, "system.ping", {}, "")

    def test_idle_run_is_clean(self):
        self.assertIsNone(ghost.run_once(self.conn, self.workspace, now=10))


if __name__ == "__main__":
    unittest.main()

