"""Offline, deterministic checks for the GitHub-hosted Hank employee."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hank_cloud_watchdog as hank
NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


def make():
    tasks = {"tasks": [
        {"id": "one", "status": "done", "evidence": [
            {k: "verified" for k in hank.EVIDENCE}]},
        {"id": "two", "status": "active", "owner": "worker",
         "next_update": "soon", "updated_at": NOW.isoformat(),
         "depends_on": ["one"]}]}
    routing = {"tasks": {"one": {}, "two": {}}}
    roles = {"roles": [{"id": x.lower()} for x in hank.ROLES]}
    provider = {"employees": [{"name": x} for x in hank.ROLES],
                "supervisor": {"employee": "Walter"},
                "control_plane": {"duplicate_scheduler_allowed": False},
                "safety": {"default_paid_use_allowed": False,
                           "legacy_failed_receipts_never_requeued": True,
                           "stop_honored_on_every_dispatch": True,
                           "existing_omniroute_rolling_24h_claim_cap": 5}}
    return [tasks, routing, roles, provider]


class HankTests(unittest.TestCase):
    def inspect(self, docs):
        return hank.audit(*docs, now=NOW)

    def test_healthy_read_only_aggregate(self):
        result = self.inspect(make())
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["tasks"], 2)
        self.assertNotIn("worker", hank.summary(result, "abc"))

    def test_bad_evidence_blocks(self):
        docs = make()
        docs[0]["tasks"][0]["evidence"][0]["check"] = ""
        self.assertIn("completed_task_evidence_invalid", self.inspect(docs)["errors"])

    def test_duplicate_ids(self):
        docs = make()
        docs[0]["tasks"].append(copy.deepcopy(docs[0]["tasks"][0]))
        self.assertIn("duplicate_task_ids", self.inspect(docs)["errors"])

    def test_missing_routing(self):
        docs = make()
        del docs[1]["tasks"]["one"]
        self.assertIn("routing_missing_or_extra", self.inspect(docs)["errors"])

    def test_stale_claim_warns_and_never_takes_ownership(self):
        docs = make()
        docs[0]["tasks"][1]["updated_at"] = (NOW - timedelta(days=4)).isoformat()
        result = self.inspect(docs)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["stale_claims"], 1)
        self.assertEqual(docs[0]["tasks"][1]["owner"], "worker")

    def test_dangerous_policy_change_blocks(self):
        docs = make()
        docs[3]["safety"]["default_paid_use_allowed"] = True
        self.assertIn("zero_spend_stop_or_scheduler_policy_changed", self.inspect(docs)["errors"])

    def test_no_stop_blocks(self):
        docs = make()
        docs[3]["safety"]["stop_honored_on_every_dispatch"] = False
        self.assertIn("zero_spend_stop_or_scheduler_policy_changed", self.inspect(docs)["errors"])

    def test_unknown_dependency(self):
        docs = make()
        docs[0]["tasks"][1]["depends_on"] = ["nonexistent"]
        self.assertIn("unknown_dependency", self.inspect(docs)["errors"])

    def test_changed_roster_blocks(self):
        docs = make()
        docs[2]["roles"].pop()
        self.assertIn("employee_roster_mismatch", self.inspect(docs)["errors"])

    def test_real_repository_invariants(self):
        c = ROOT / "coordination"
        docs = [hank.loaded(c / x) for x in (
            "tasks.json", "work-routing.json",
            "ghost-role-bootstrap.json", "ghost-provider-policy.json")]
        result = self.inspect(docs)
        self.assertEqual(result["status"], "healthy", str(result["errors"]))


if __name__ == "__main__":
    unittest.main()
