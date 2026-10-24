"""No-network multi-specialist regression: one service, shared SQLite, unique claims."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ghost_worker as worker
import ghost_worker_loop as loop
import ghost_omniroute_feed as feed
import ghost_omniroute_job as omni


class ParallelClaims(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name) / "private-state"
        self.db = worker.connect(self.state)
        self.addCleanup(self.db.close)

    def test_parallel_never_enabled_by_default_or_model_only_approval(self):
        for kwargs in (
                {"parallel_omniroute_workers": 2},
                {"parallel_omniroute_workers": 3, "allow_omniroute_model_use": True},
                {"parallel_omniroute_workers": 4, "allow_omniroute_work_plan": True,
                 "allow_omniroute_model_use": True},
                {"parallel_omniroute_workers": 2, "allow_omniroute_work_plan": True,
                 "allow_omniroute_model_use": True, "max_jobs": 1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    loop.poll(self.db, ROOT, self.state, worker_id="test", **kwargs)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)

    def test_exactly_three_distinct_review_only_packet_claims(self):
        seen = []
        def complete(state, job_id, payload, **_kwargs):
            seen.append((job_id, payload["packet"]))
            return {"draft_status": "draft_completed_needs_review",
                    "review_status": "draft_ready_for_human_review",
                    "packet": payload["packet"]}
        with mock.patch.object(omni, "execute", side_effect=complete):
            report = loop.poll(
                self.db, ROOT, self.state, worker_id="mac-workers",
                max_jobs=3, max_seconds=2, poll_seconds=1,
                allow_omniroute_model_use=True, allow_omniroute_work_plan=True,
                parallel_omniroute_workers=3)
        self.assertEqual(report["executed"], 3)
        self.assertEqual(report["parallel_workers"], 3)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["review_ready"], 3)
        self.assertEqual(report["needs_review"], 3)
        self.assertEqual(len(seen), 3)
        self.assertEqual(len({j[0] for j in seen}), 3)
        self.assertEqual(len({j[1] for j in seen}), 3)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='needs_review'").fetchone()[0], 3)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0], 3)

    def test_quota_is_atomic_and_no_sixth_claim_even_in_parallel(self):
        for i in range(4):
            job = worker.enqueue(self.db, worker.OMNI_KIND,
                                 {"packet": "runner-blocker"}, "legacy-" + str(i))
            claim = worker.claim(self.db, "prior", allow_omniroute_model_use=True)
            self.assertIsNotNone(claim)
            self.db.execute("UPDATE jobs SET status='needs_review' WHERE id=?", (job,))
        calls = []
        with mock.patch.object(omni, "execute", side_effect=lambda state, job_id, payload, **kw:
                               (calls.append(job_id) or {"draft_status": "draft_completed_needs_review"})):
            result = loop.poll(self.db, ROOT, self.state, worker_id="quota",
                               max_jobs=3, max_seconds=2, poll_seconds=1,
                               allow_omniroute_model_use=True,
                               allow_omniroute_work_plan=True,
                               parallel_omniroute_workers=3)
        self.assertEqual(result["executed"], 1)
        self.assertEqual(result["review_ready"], 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0], 5)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0], 2)

    def test_owner_approved_higher_free_budget_runs_beyond_old_five(self):
        for i in range(5):
            worker.enqueue(self.db, worker.OMNI_KIND,
                           {"packet": "runner-blocker"}, "used-" + str(i))
            prior = worker.claim(self.db, "prior", allow_omniroute_model_use=True)
            self.assertIsNotNone(prior)
            self.db.execute("UPDATE jobs SET status='needs_review' WHERE id=?",
                            (prior["id"],))
        calls=[]
        def completes(state, job_id, payload, **_):
            calls.append(job_id)
            return {"draft_status":"draft_completed_needs_review",
                    "review_status":"draft_ready_for_human_review"}
        with mock.patch.object(omni, "execute", side_effect=completes):
            response=loop.poll(self.db, ROOT, self.state, worker_id="expanded",
                               max_jobs=3,max_seconds=2,poll_seconds=1,
                               allow_omniroute_model_use=True,
                               allow_omniroute_work_plan=True,
                               parallel_omniroute_workers=3, omni_max_24h=14)
        self.assertEqual(response["executed"],3)
        self.assertEqual(response["max_free_model_claims_24h"],14)
        self.assertEqual(len(calls),3)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0],8)
        with self.assertRaises(ValueError):
            worker.claim(self.db,"invalid",allow_omniroute_model_use=True,
                         omni_max_24h=21)

    def test_existing_stop_refuses_all_new_parallel_work(self):
        (self.state / "STOP").write_text("stop")
        report = loop.poll(self.db, ROOT, self.state, worker_id="stop",
                           max_jobs=3, max_seconds=2, poll_seconds=1,
                           allow_omniroute_model_use=True, allow_omniroute_work_plan=True,
                           parallel_omniroute_workers=3)
        self.assertEqual(report["executed"], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
