"""Recovery canary does not replay prior jobs or permit silent circuit bypass."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import ghost_worker as worker
import ghost_omniroute_feed as feed
import ghost_omniroute_job as omni
import omniroute_recovery_canary as canary


def catalog():
    return [{"name":name,"strategy":"priority","isHidden":False,
             "models":[{"kind":"model","providerId":"openrouter","model":m}
                       for m in models]}
            for name,models in dict.fromkeys(omni.ROUTES.values())]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.state=Path(temp.name).resolve()/"private-state"
        self.db=worker.connect(self.state)
        self.addCleanup(self.db.close)
        self.work=Path(temp.name).resolve()/"workspace"
        self.work.mkdir()

    def run_canary(self, **args):
        return canary.run(state=self.state,root=ROOT,workspace=self.work,
                          get_db=lambda state:worker.connect(state),
                          read_combo=catalog,**args)

    def test_no_approval_never_touches_queue_or_calls_models(self):
        reply=self.run_canary()
        self.assertEqual(reply["status"],"requires_both_owner_approvals")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],0)

    def test_circuit_override_only_allows_new_exact_canary_one_time(self):
        for i in range(3):
            j=worker.enqueue(self.db,worker.OMNI_KIND,
                             {"packet":"runner-blocker"},"failed-"+str(i))
            claimed=worker.claim(self.db,"old",allow_omniroute_model_use=True)
            self.assertIsNotNone(claimed)
            self.db.execute("UPDATE jobs SET status='needs_review',result=? WHERE id=?",
                            (json.dumps({"draft_status":"needs_review_no_auto_retry"}),j))
        with mock.patch.object(omni,"execute",return_value={
            "packet":"walter-v2-recovery-proof",
            "draft_status":"draft_completed_needs_review",
            "review_status":"draft_ready_for_human_review"}) as model:
            result=self.run_canary(approve=True,acknowledge_circuit=True)
            self.assertEqual(result["status"],"completed_requires_human_review")
            self.assertEqual(result["model_request_count"],1)
            model.assert_called_once()
            # Calling the command twice must NEVER trigger a second request.
            repeated=self.run_canary(approve=True,acknowledge_circuit=True)
            self.assertEqual(repeated["status"],"canary_already_claimed_never_retry")
            model.assert_called_once()
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE kind=?",(worker.OMNI_KIND,)).fetchone()[0],4)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0],4)

    def test_manual_override_cannot_claim_arbitrary_or_historical_omni_job(self):
        prior=worker.enqueue(self.db,worker.OMNI_KIND,{"packet":"runner-blocker"},
                             "old-unrelated")
        with self.assertRaisesRegex(ValueError,"Recovery canary ID"):
            worker.claim(self.db,"bad",allow_omniroute_model_use=True,
                         omniroute_queue_job_id=prior,allow_recovery_canary=True)
        self.assertEqual(self.db.execute(
            "SELECT status FROM jobs WHERE id=?",(prior,)).fetchone()[0],"queued")
        with self.assertRaisesRegex(ValueError,"Manual recovery"):
            worker.claim(self.db,"bad",allow_omniroute_model_use=True,
                         allow_recovery_canary=True)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0],0)

    def test_owner_stop_never_creates_canary(self):
        (self.state/"STOP").write_text("stop")
        result=self.run_canary(approve=True,acknowledge_circuit=True)
        self.assertEqual(result["status"],"owner_stop_present")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],0)

    def test_quota_still_blocks_one_time_manual_recovery(self):
        for i in range(14):
            j=worker.enqueue(self.db,worker.OMNI_KIND,{"packet":"runner-blocker"},
                             "used-"+str(i))
            cl=worker.claim(self.db,"used",allow_omniroute_model_use=True,
                            omni_max_24h=14)
            self.assertIsNotNone(cl)
            self.db.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(j,))
        with mock.patch.object(omni,"execute") as call:
            result=self.run_canary(approve=True,acknowledge_circuit=True)
            self.assertEqual(result["status"],"no_claim_circuit_quota_or_stop")
            call.assert_not_called()


if __name__=="__main__": unittest.main()
