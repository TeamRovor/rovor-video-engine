"""Deterministic tests for bounded, foreground ROVOR ghost worker polling."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import ghost_worker as worker  # noqa: E402
import ghost_worker_loop as loop  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class WorkerLoopTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        home = Path(self.t.name)
        self.state = home / "state"
        self.workspace = home / "sandbox"
        self.workspace.mkdir()
        self.db = worker.connect(self.state)
        self.addCleanup(self.db.close)

    def run_loop(self, clock=None, **kwargs):
        clock = clock or FakeClock()
        return loop.poll(self.db, self.workspace, self.state, worker_id="test-loop",
                         monotonic=clock.monotonic, sleeper=clock.sleep, **kwargs)

    def test_processes_queued_jobs_and_stops_at_job_budget(self):
        ids = [worker.enqueue(self.db, "system.ping", {}, f"ping-{i}") for i in range(3)]
        result = self.run_loop(max_jobs=2)
        self.assertEqual((result["executed"], result["succeeded"], result["stop_reason"]),
                         (2, 2, "max_jobs"))
        counts = dict(self.db.execute("SELECT status,count(*) FROM jobs GROUP BY status").fetchall())
        self.assertEqual(counts, {"queued": 1, "succeeded": 2})
        self.assertEqual(len(set(ids)), 3)

    def test_empty_queue_sleeps_without_busy_spin(self):
        clock = FakeClock()
        result = self.run_loop(clock=clock, max_seconds=2.5, poll_seconds=1)
        self.assertEqual(result["stop_reason"], "max_seconds")
        self.assertEqual(clock.sleeps, [1, 1, 0.5])
        self.assertEqual(result["executed"], 0)
        self.assertEqual(result["idle_polls"], 3)

    def test_stop_existing_before_jobs_run(self):
        worker.enqueue(self.db, "system.ping", {}, "queued")
        self.assertTrue(loop.request_stop(self.state))
        self.assertFalse(loop.request_stop(self.state))
        result = self.run_loop()
        self.assertEqual(result["stop_reason"], "stop_requested")
        self.assertEqual(result["executed"], 0)
        self.assertEqual(self.db.execute("SELECT status FROM jobs").fetchone()[0], "queued")

    def test_stop_during_idle_check(self):
        clock = FakeClock()
        def sleeping(delay):
            clock.sleep(delay)
            loop.request_stop(self.state)
        result = loop.poll(self.db, self.workspace, self.state, worker_id="test-loop",
                           max_seconds=100, poll_seconds=5,
                           monotonic=clock.monotonic, sleeper=sleeping)
        self.assertEqual(result["stop_reason"], "stop_requested")
        self.assertEqual(clock.sleeps, [5])

    def test_resume_does_not_start_jobs(self):
        worker.enqueue(self.db, "system.ping", {}, "resume")
        loop.request_stop(self.state)
        self.assertTrue(loop.clear_stop(self.state))
        self.assertFalse(loop.clear_stop(self.state))
        self.assertEqual(self.db.execute("SELECT status FROM jobs").fetchone()[0], "queued")
        self.assertEqual(self.run_loop(max_jobs=1)["succeeded"], 1)

    def test_limits_reject_unsafe_inputs(self):
        for options in [dict(max_jobs=0,max_seconds=1,poll_seconds=1),
                        dict(max_jobs=1001,max_seconds=1,poll_seconds=1),
                        dict(max_jobs=True,max_seconds=1,poll_seconds=1),
                        dict(max_jobs=1,max_seconds=3601,poll_seconds=1),
                        dict(max_jobs=1,max_seconds=1,poll_seconds=0),
                        dict(max_jobs=1,max_seconds=1,poll_seconds=31),
                        dict(max_jobs=1,max_seconds=float("nan"),poll_seconds=1)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                loop.validate_limits(**options)

    def test_bad_stop_marker_fails_closed(self):
        target = Path(self.t.name) / "outside"
        target.write_text("outside")
        (self.state / "STOP").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            loop.request_stop(self.state)
        with self.assertRaisesRegex(ValueError, "symlink"):
            loop.clear_stop(self.state)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_loop()
        self.assertEqual(target.read_text(), "outside")

    def test_state_symlink_rejected(self):
        bad = Path(self.t.name) / "redirect"
        bad.symlink_to(self.state, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            loop.request_stop(bad)

    def test_restart_reuses_queue_and_receipts(self):
        job = worker.enqueue(self.db, "system.ping", {}, "resumed")
        self.db.close()
        self.db = worker.connect(self.state)
        self.assertEqual(self.run_loop(max_jobs=1)["succeeded"], 1)
        self.db.close()
        self.db = worker.connect(self.state)
        self.assertEqual(self.db.execute("SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "succeeded")
        self.assertEqual(self.db.execute("SELECT count(*) FROM events WHERE job_id=?", (job,)).fetchone()[0], 3)

    def test_expired_readonly_lease_recovers(self):
        jid=worker.enqueue(self.db,"system.ping",{},"leased",now=1)
        worker.claim(self.db,"missing-worker",now=10)
        # Original reader died. Replay is permitted only after lease expiry.
        self.assertIsNone(worker.claim(self.db,"second-worker",now=11))
        self.assertEqual(worker.claim(self.db,"second-worker",now=131)["id"], jid)
        self.assertEqual(self.db.execute("SELECT attempts FROM jobs WHERE id=?", (jid,)).fetchone()[0], 2)

    def test_disabled_actions_stay_disabled(self):
        for kind in ["social.publish", "email.send", "files.move", "moho.animate", "blender.scene"]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                worker.enqueue(self.db, kind, {}, "disabled:"+kind)
        self.assertEqual(self.run_loop(max_seconds=0.1)["executed"], 0)

    def test_failed_adapter_receipt_counts_as_job(self):
        worker.enqueue(self.db,"files.inventory",{"subpath":"../private"},"failure")
        result = self.run_loop(max_jobs=1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["stop_reason"], "max_jobs")
        self.assertEqual(self.db.execute("SELECT status FROM jobs").fetchone()[0], "failed")

    def test_two_workers_never_execute_same_job(self):
        n = 20
        for i in range(n):
            worker.enqueue(self.db,"system.ping",{},f"thread-{i}")
        def take_once(i):
            with closing(worker.connect(self.state)) as conn:
                return worker.run_once(conn, self.workspace, owner=f"thread-{i}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(take_once, range(n)))
        self.assertEqual(len([r for r in receipts if r and r["status"]=="succeeded"]),n)
        self.assertEqual(len({r["id"] for r in receipts if r}),n)
        self.assertEqual(self.db.execute("SELECT count(*) FROM jobs WHERE status='succeeded'").fetchone()[0],n)
        self.assertEqual(self.db.execute("SELECT sum(attempts) FROM jobs").fetchone()[0],n)

if __name__ == "__main__":
    unittest.main()
