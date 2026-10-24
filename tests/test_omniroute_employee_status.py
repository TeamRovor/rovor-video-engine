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

    def test_stop_reported_without_resuming_worker(self):
        (self.state/"STOP").write_text("owner stopped")
        obj=status.inspect(self.state,run=lambda *args,**kwargs: type("X",(),{"returncode":1})())
        self.assertTrue(obj["stop_requested"])
        self.assertFalse(obj["launchagent_loaded"])
        self.assertTrue((self.state/"STOP").is_file())


if __name__=="__main__":
    unittest.main()
