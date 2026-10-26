"""Offline, deterministic checks for the GitHub-hosted Hank employee."""
import copy
import hashlib
import json
import os
import tempfile
from unittest.mock import patch
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


    def receipt_fixture(self, base):
        root = Path(base) / "coordination"
        root.mkdir()
        for name, value in zip(hank.RECEIPT_INPUTS, make()):
            (root / name).write_text(json.dumps(value), encoding="utf-8")
        return root

    def create_receipt(self, root, report=None, **changes):
        params = {"commit": "a" * 40, "run_id": "40140000000",
                  "attempt": 1, "observed_at": NOW}
        params.update(changes)
        return hank.cloud_receipt(report or self.inspect(make()), root, **params)

    def test_cloud_receipt_is_bounded_and_content_free(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            result = self.create_receipt(root)
            self.assertEqual(result["employee"], "Hank")
            self.assertEqual(result["execution_source"], "github_actions")
            self.assertEqual(result["github_run_id"], "40140000000")
            self.assertEqual(result["status"], "healthy")
            self.assertEqual(result["human_review"], "not_recorded")
            self.assertIsNone(result["model"])
            self.assertIsNone(result["tokens"])
            self.assertFalse(result["mac_runtime_verified"])
            self.assertFalse(result["omniroute_inference_verified"])
            self.assertEqual(result["public_input_sha256"]["tasks.json"],
                             hashlib.sha256((root / "tasks.json").read_bytes()).hexdigest())
            encoded = json.dumps(result)
            self.assertLess(len(encoded.encode("utf-8")), 4096)
            self.assertNotIn("worker", encoded)
            self.assertNotIn(str(root), encoded)

    def test_cloud_receipt_records_failed_audit_without_false_success(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            docs = make()
            docs[3]["safety"]["default_paid_use_allowed"] = True
            failed = self.inspect(docs)
            result = self.create_receipt(root, failed)
            self.assertEqual(result["status"], "needs_review")
            self.assertIn("zero_spend_stop_or_scheduler_policy_changed", result["errors"])

    def test_cloud_receipt_rejects_invalid_provenance(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            for override in (
                {"commit": "a" * 39},
                {"commit": "A" * 40},
                {"run_id": "0"},
                {"run_id": "1; rm -rf"},
                {"attempt": 0},
                {"attempt": True},
                {"observed_at": NOW.replace(tzinfo=None)},
            ):
                with self.subTest(override=override):
                    with self.assertRaisesRegex(ValueError, "receipt_provenance_invalid"):
                        self.create_receipt(root, **override)

    def test_cloud_receipt_rejects_injected_codes_and_counts(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            for patch_data in (
                {"errors": ["private /home/user/secret"]},
                {"warnings": ["\\nInjected"]},
                {"counts": {"active": True}},
                {"counts": {"custom": 1}},
                {"tasks": -1},
                {"status": "approved"},
                {"status": "healthy", "errors": ["unknown_error"]},
            ):
                with self.subTest(patch_data=patch_data):
                    report = dict(self.inspect(make()), **patch_data)
                    with self.assertRaisesRegex(ValueError, "receipt_report_invalid"):
                        self.create_receipt(root, report)

    def test_cloud_receipt_rejects_redirected_or_oversized_source(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            original = root / "tasks.json"
            original.unlink()
            original.symlink_to(root / "work-routing.json")
            with self.assertRaisesRegex(ValueError, "receipt_sources_invalid"):
                self.create_receipt(root)
            original.unlink()
            original.write_bytes(b"x" * 5000001)
            with self.assertRaisesRegex(ValueError, "receipt_sources_invalid"):
                self.create_receipt(root)

    def test_cloud_receipt_requires_source_digest_for_healthy_audit(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            (root / "tasks.json").unlink()
            with self.assertRaisesRegex(ValueError, "receipt_sources_invalid"):
                self.create_receipt(root)
            failed = dict(self.inspect(make()), status="needs_review",
                          errors=["source_unavailable"])
            result = self.create_receipt(root, failed)
            self.assertIsNone(result["public_input_sha256"]["tasks.json"])

    def test_cli_writes_actual_hosted_receipt_only_with_actions_provenance(self):
        with tempfile.TemporaryDirectory() as base:
            root = self.receipt_fixture(base)
            output = Path(base) / "hank.json"
            env = {"GITHUB_ACTIONS": "true", "GITHUB_SHA": "b" * 40,
                   "GITHUB_RUN_ID": "40140000001", "GITHUB_RUN_ATTEMPT": "2"}
            with patch.dict(os.environ, env):
                self.assertEqual(hank.main(["--root", base, "--receipt-file", str(output)]), 0)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["github_run_attempt"], 2)
            self.assertEqual(receipt["commit_sha"], "b" * 40)
            output.unlink()
            with patch.dict(os.environ, dict(env, GITHUB_ACTIONS="false")):
                self.assertEqual(hank.main(["--root", base, "--receipt-file", str(output)]), 1)
            self.assertFalse(output.exists())

    def test_real_repository_invariants(self):
        c = ROOT / "coordination"
        docs = [hank.loaded(c / x) for x in (
            "tasks.json", "work-routing.json",
            "ghost-role-bootstrap.json", "ghost-provider-policy.json")]
        result = self.inspect(docs)
        self.assertEqual(result["status"], "healthy", str(result["errors"]))


if __name__ == "__main__":
    unittest.main()
