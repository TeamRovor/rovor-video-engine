import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hud_employee_snapshot import read_dispatch

class WorkerPacingSnapshot(unittest.TestCase):
    def test_recent_report_and_stale_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            file = base / "continuous-status.json"
            report = {"observed_at": 1000, "executed": 0,
                      "dispatch": {"reason": "paced_wait",
                                   "claims_last_24h": 46, "max_claims_24h": 50,
                                   "queued": 1, "running": 0,
                                   "next_eligible_at": 1500,
                                   "job_counts": {"needs_review": 92},
                                   "secret": "SHOULD_NOT_APPEAR"}}
            file.write_text(json.dumps(report))
            result = read_dispatch(base, 1005, {"recent": True})
            self.assertEqual(result["status"], "recent_scheduler_report")
            self.assertEqual(result["reason"], "paced_wait")
            self.assertEqual(result["claims_last_24h"], 46)
            self.assertEqual(result["needs_review"], 92)
            self.assertEqual(result["last_tick_executed"], 0)
            self.assertNotIn("SHOULD_NOT_APPEAR", str(result))
            self.assertEqual(read_dispatch(base, 2500, {"recent": True})["status"],
                             "unavailable_or_stale")
            self.assertEqual(read_dispatch(base, 1005, {"recent": False})["status"],
                             "unavailable_or_stale")
            file.unlink()
            file.symlink_to(base / "missing")
            self.assertEqual(read_dispatch(base, 1005, {"recent": True})["status"],
                             "unavailable_or_stale")

if __name__ == "__main__":
    unittest.main()
