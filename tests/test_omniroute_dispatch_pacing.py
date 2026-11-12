import json
from pathlib import Path
import plistlib
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_dispatch_pacing as pace


class PacingTests(unittest.TestCase):
    def decide(self, **kw):
        args = dict(now=100000, claims=[], max_claims=14, queued=3)
        args.update(kw)
        return pace.dispatch_decision(**args)

    def test_actual_fourteen_claim_stall_and_exact_release(self):
        claims = [20000.25 + n * 10 for n in range(14)]
        result = self.decide(claims=claims)
        self.assertEqual(result["reason"], "rolling_quota")
        self.assertEqual(result["next_eligible_at"], 106401)
        self.assertTrue(self.decide(now=106401, claims=claims)["allowed"])

    def test_over_limit_needs_enough_claims_to_expire(self):
        result = self.decide(claims=[20000 + n for n in range(17)])
        self.assertEqual(result["next_eligible_at"], 106404)

    def test_inclusive_day_boundary_does_not_dispatch_early(self):
        self.assertFalse(self.decide(now=86400, claims=[0], max_claims=1)["allowed"])
        self.assertTrue(self.decide(now=86401, claims=[0], max_claims=1)["allowed"])

    def test_pacing_waits_even_with_free_daily_capacity(self):
        result = self.decide(claims=[99900], pace_seconds=600)
        self.assertEqual(result["reason"], "paced_wait")
        self.assertEqual(result["next_eligible_at"], 100500)

    def test_quota_and_pace_wait_for_both(self):
        result = self.decide(claims=[20000], max_claims=1, pace_seconds=90000)
        self.assertEqual(result["next_eligible_at"], 110000)

    def test_small_and_large_budgets_sustain_seven_days_without_daily_stall(self):
        for budget in (14, 20, 144):
            interval = pace.recommended_interval(budget)
            claims = []
            for n in range(budget * 7):
                now = n * interval
                result = self.decide(now=now, max_claims=budget,
                                     claims=claims, pace_seconds=interval)
                self.assertTrue(result["allowed"], (budget, n, result))
                claims.append(now)
                active = [t for t in claims if t >= now - pace.DAY]
                self.assertLessEqual(len(active), budget)

    def test_stop_circuit_running_and_empty_queue_have_no_false_wakeup(self):
        for arg, reason in (({"stopped": True}, "stop_requested"),
                            ({"circuit_open": True}, "failure_circuit_requires_review"),
                            ({"running": 1}, "existing_work_running"),
                            ({"queued": 0}, "no_queued_work")):
            result = self.decide(**arg)
            self.assertFalse(result["allowed"])
            self.assertEqual(result["reason"], reason)
            self.assertIsNone(result["next_eligible_at"])

    def test_bad_evidence_fails_closed(self):
        for kw in ({"max_claims": True}, {"now": float("nan")},
                   {"claims": [100001]}, {"claims": [float("inf")]},
                   {"claims": [True]}, {"pace_seconds": -1},
                   {"queued": True}, {"stopped": 1}, {"claims": None}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.decide(**kw)


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.db = self.state / "jobs.sqlite3"
        self.conn = sqlite3.connect(self.db)
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript("CREATE TABLE jobs(id,kind,status,result);"
                                "CREATE TABLE events(id,job_id,event,timestamp);")
        for n in range(14):
            self.conn.execute("INSERT INTO jobs VALUES(?,?,?,?)",
                              (str(n), "research.omniroute", "needs_review",
                               json.dumps({"draft_status": "draft_completed_needs_review",
                                           "secret": "DO_NOT_PRINT"})))
            self.conn.execute("INSERT INTO events VALUES(?,?,?,?)",
                              (n, str(n), "claimed", 20000.25 + n * 10))
        for n in range(3):
            self.conn.execute("INSERT INTO jobs VALUES(?,?,?,?)",
                              ("queued" + str(n), "research.omniroute", "queued", None))
        self.conn.commit()
        self.plist = self.root / "worker.plist"
        self.plist.write_bytes(plistlib.dumps({"Label": pace.LABEL,
            "ProgramArguments": ["python3", "/runtime/tools/ghost_worker_loop.py",
                                 "--state", str(self.state), "run",
                                 "--max-omniroute-claims-per-day", "14"],
            "StartInterval": 300}))

    def test_live_wal_snapshot_includes_recent_claims_without_modifying_source(self):
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        result = pace.read_health(self.plist, now=100000)
        self.assertEqual(result["reason"], "rolling_quota")
        self.assertEqual(result["queued"], 3)
        self.assertEqual(result["claims_last_24h"], 14)
        self.assertFalse(result["pacing_installed"])
        self.assertNotIn("DO_NOT_PRINT", json.dumps(result))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.state.iterdir()})

    def test_persistent_stop_does_not_claim_or_resume(self):
        (self.state / "STOP").touch()
        self.assertEqual(pace.read_health(self.plist, now=100000)["reason"], "stop_requested")
        self.assertTrue((self.state / "STOP").exists())

    def test_three_recorded_failures_need_review_not_a_timed_retry(self):
        self.conn.execute("UPDATE jobs SET result=? WHERE id IN ('11','12','13')",
                          (json.dumps({"draft_status": "needs_review_no_auto_retry"}),))
        self.conn.commit()
        result = pace.read_health(self.plist, now=100000)
        self.assertEqual(result["reason"], "failure_circuit_requires_review")
        self.assertIsNone(result["earliest_eligible_utc"])

    def test_symlinked_db_is_rejected(self):
        self.conn.close()
        self.db.rename(self.state / "real.sqlite3")
        self.db.symlink_to(self.state / "real.sqlite3")
        with self.assertRaises(ValueError):
            pace.read_health(self.plist, now=100000)


if __name__ == "__main__":
    unittest.main()
