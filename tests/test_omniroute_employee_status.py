"""Status report displays only sanitized DB/launchctl metadata."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
import omniroute_employee_status as status


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)/"state"
        self.state.mkdir()
        db=sqlite3.connect(str(self.state/"jobs.sqlite3"))
        db.executescript("""
        CREATE TABLE jobs(id TEXT,kind TEXT,status TEXT,payload TEXT,result TEXT);
        CREATE TABLE events(job_id TEXT,event TEXT,timestamp REAL);
        """)
        db.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                   ("one","research.omniroute","needs_review",
                    json.dumps({"packet":"walter-v1-moho-viseme-review"}),
                    json.dumps({"draft_status":"draft_completed_needs_review",
                                "review_status":"draft_ready_for_human_review",
                                "answer":"PRIVATE_DRAFT_SHOULD_NOT_LEAK"})))
        db.commit()
        db.close()

    def test_sanitized_evidence_only(self):
        class Result:
            returncode=0
            stdout="state = not running\nruns = 33\nlast exit code = 0\nsecret=x"
        obj=status.inspect(self.state, run=lambda *args,**kwargs:Result())
        self.assertEqual(obj["launchagent_loaded"],True)
        self.assertEqual(obj["runs"],33)
        self.assertEqual(obj["specialists"]["jesse"],{"needs_review":1})
        self.assertEqual(obj["omniroute_draft_counts"],{"review_ready":1})
        self.assertEqual(obj["database_status"],"snapshot_readable")
        self.assertNotIn("PRIVATE_DRAFT_SHOULD_NOT_LEAK",json.dumps(obj))

    def test_live_wal_database_uses_consistent_read_only_backup(self):
        # Retain an active WAL writer and its sidecars, exactly like the
        # owner's Mac service. No STOP/restart/checkpoint is requested.
        with sqlite3.connect(str(self.state/"jobs.sqlite3")) as writer:
            self.assertEqual(writer.execute(
                "PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                           ("two", "research.omniroute", "queued",
                            json.dumps({"packet":"walter-v1-safe-client-intake"}),
                            None))
            writer.commit()
            wal = self.state / "jobs.sqlite3-wal"
            shm = self.state / "jobs.sqlite3-shm"
            self.assertTrue(wal.is_file())
            self.assertTrue(shm.is_file())
            before = writer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            result = status.inspect(self.state,
                run=lambda *args, **kwargs: type("R",(),{
                    "returncode":0,"stdout":"runs = 2\\nlast exit code = 0"})())
            after = writer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            self.assertEqual(result["database_status"],"snapshot_readable")
            self.assertEqual(result["specialists"]["gus"],{"queued":1})
            self.assertEqual(result["specialists"]["jesse"],{"needs_review":1})
            self.assertEqual(result["omniroute_draft_counts"],{"review_ready":1})
            self.assertEqual((before,after),(2,2))
            self.assertTrue(wal.exists())
            self.assertTrue(shm.exists())
            self.assertNotIn("PRIVATE_DRAFT_SHOULD_NOT_LEAK",json.dumps(result))

    def test_incomplete_wal_sidecars_do_not_use_inconsistent_copy(self):
        (self.state/"jobs.sqlite3-wal").write_bytes(b"not a real WAL")
        result=status.inspect(self.state,run=lambda *a, **k:
                              type("R",(),{"returncode":1})())
        self.assertEqual(result["database_status"],"incomplete_wal_sidecars")
        self.assertNotIn("job_status_counts",result)

    def test_symlinked_wal_file_is_rejected_without_following(self):
        secret=self.state/"private-data"
        secret.write_text("do not read")
        (self.state/"jobs.sqlite3-wal").symlink_to(secret)
        result=status.inspect(self.state,run=lambda *a, **k:
                              type("R",(),{"returncode":1})())
        self.assertEqual(result["database_status"],"unsafe_database_sidecar")
        self.assertNotIn("private-data",json.dumps(result))

    def test_sanitized_failed_specialist_receipt_reports_class_and_elapsed_bucket(self):
        job_id = "a1111111-2222-3333-4444-555555555555"
        slug = "walter-v1-moho-viseme-review"
        receipt_dir = self.state / "omniroute-drafts" / job_id
        receipt_dir.mkdir(parents=True)
        (receipt_dir / (slug + ".receipt.json")).write_text(json.dumps({
            "id": "walter-public-v1-moho-viseme-review",
            "status": "needs_review_no_auto_retry",
            "error_class": "ValueError",
            "elapsed_seconds": 3.4,
            "answer": "CONFIDENTIAL_OUTPUT_MUST_NOT_LEAK",
        }))
        db = sqlite3.connect(str(self.state/"jobs.sqlite3"))
        db.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                   (job_id, "research.omniroute", "needs_review",
                    json.dumps({"packet": slug}),
                    json.dumps({"draft_status": "needs_review_no_auto_retry",
                                "review_status": "failed_needs_review",
                                "receipt": "/private/secret"})))
        db.commit()
        db.close()
        got = status.inspect(self.state, run=lambda *args, **kwargs:
                             type("X",(),{"returncode":1})())
        self.assertEqual(got["nonready_reason_counts"], {
            "draft:needs_review_no_auto_retry": 1,
            "review:failed_needs_review": 1,
            "exception:ValueError": 1})
        self.assertEqual(got["nonready_elapsed_buckets"], {"1_to_15s":1})
        self.assertNotIn("CONFIDENTIAL_OUTPUT_MUST_NOT_LEAK", json.dumps(got))
        self.assertNotIn("/private/secret", json.dumps(got))

    def test_reporting_matches_three_failure_claim_circuit_without_model_calls(self):
        import time
        db = sqlite3.connect(str(self.state/"jobs.sqlite3"))
        now = time.time()
        for i in range(3):
            uid = "test-" + str(i)
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",
                       (uid,"research.omniroute","needs_review",
                        json.dumps({"packet":"walter-v1-mac-worker-stop-recovery"}),
                        json.dumps({"draft_status":"needs_review_no_auto_retry",
                                    "review_status":"failed_needs_review"})))
            db.execute("INSERT INTO events VALUES(?,?,?)",
                       (uid,"claimed",now - 20 + i))
        db.commit()
        db.close()
        result = status.inspect(self.state, run=lambda *a, **k:
                                type("R",(),{"returncode":1})())
        self.assertEqual(result["consecutive_recorded_inference_failures"],3)
        self.assertTrue(result["inference_claim_guard_would_block"])
        self.assertEqual(result["ai_claims_last_24h"],3)

    def test_stop_reported_without_resuming_worker(self):
        (self.state/"STOP").write_text("owner stopped")
        obj=status.inspect(self.state,run=lambda *args,**kwargs: type("X",(),{"returncode":1})())
        self.assertTrue(obj["stop_requested"])
        self.assertFalse(obj["launchagent_loaded"])
        self.assertTrue((self.state/"STOP").is_file())


if __name__=="__main__":
    unittest.main()
