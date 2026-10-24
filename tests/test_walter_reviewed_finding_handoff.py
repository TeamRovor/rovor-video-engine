"""Offline checks for human-reviewed, deduplicated research-to-code handoffs."""
import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_reviewed_finding_handoff import HandoffError, propose

SOURCE = "one\nThis public source documents a review-only receipt gate.\nthree\n"
DIGEST = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
TARGET = "tools/example_worker.py"
TARGET_SHA = "a" * 64
PROBLEM = ("The existing example worker silently marks an empty model receipt "
           "as completed even when no visible text was produced.")
CHANGE = ("Add a fail closed check in the example worker receipt validator "
          "before any completed status is recorded for the job.")
ACCEPTANCE = ("An offline unit test rejects a blank response and preserves "
              "the original receipt without changing the queue.")


def fixture():
    finding = {
        "role": "gale", "finding_key": "worker-missing-receipt",
        "change_type": "bugfix", "source_path": "WORK.md",
        "source_line_start": 2, "source_line_end": 2,
        "source_sha256": DIGEST, "target_path": TARGET,
        "target_sha256": TARGET_SHA, "test_path": "tests/test_example_worker.py",
        "subsystem": "subsystem:example-worker-regression",
        "problem": PROBLEM, "change": CHANGE, "acceptance": ACCEPTANCE,
    }
    kwargs = {
        "review_receipt": {"job_id": "verified-private-job-01",
                           "status": "human_approved",
                           "finding_key": finding["finding_key"],
                           "source_sha256": DIGEST},
        "trusted_human_review": True,
        "public_sources": {"WORK.md": SOURCE},
        "request_source_sha256": {"WORK.md": DIGEST},
        "repo_file_sha256": {TARGET: TARGET_SHA},
        "existing_tasks": [],
        "trusted_queue_snapshot": True,
    }
    return finding, kwargs


class HandoffTests(unittest.TestCase):
    def check_block(self, expected, finding=None, kwargs=None):
        base, params = fixture()
        if finding is not None:
            base.update(finding)
        if kwargs is not None:
            params.update(kwargs)
        with self.assertRaises(HandoffError) as context:
            propose(base, **params)
        self.assertEqual(str(context.exception), expected)

    def test_good_candidate_is_inert(self):
        finding, params = fixture()
        result = propose(finding, **params)
        self.assertEqual(result["status"], "reviewed_candidate_requires_separate_claim")
        self.assertEqual(result["candidate"]["target_path"], TARGET)
        self.assertTrue(result["requires_fresh_atomic_queue_claim"])
        self.assertFalse(result["automatic_approval_or_publication"])
        self.assertFalse(result["mac_execution"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)

    def test_citation_binds_exact_source_lines(self):
        finding, params = fixture()
        result = propose(finding, **params)
        self.assertEqual(result["candidate"]["source_reference"],
                         {"path": "WORK.md", "start_line": 2, "end_line": 2,
                          "source_sha256": DIGEST})

    def test_no_raw_finding_text_returned(self):
        finding, params = fixture()
        result = repr(propose(finding, **params))
        for private in (PROBLEM, CHANGE, ACCEPTANCE, "verified-private-job-01"):
            self.assertNotIn(private, result)

    def test_missing_human_review(self):
        self.check_block("independent_human_review_required",
                         kwargs={"trusted_human_review": False})

    def test_untrusted_queue(self):
        self.check_block("authoritative_queue_required",
                         kwargs={"trusted_queue_snapshot": False})

    def test_review_receipt_not_approved(self):
        _, params = fixture()
        params["review_receipt"]["status"] = "needs_review"
        self.check_block("review_receipt_unverified", kwargs=params)

    def test_review_receipt_wrong_key(self):
        _, params = fixture()
        params["review_receipt"]["finding_key"] = "another-finding"
        self.check_block("review_receipt_unverified", kwargs=params)

    def test_review_receipt_wrong_source(self):
        _, params = fixture()
        params["review_receipt"]["source_sha256"] = "b" * 64
        self.check_block("review_receipt_unverified", kwargs=params)

    def test_untrusted_source_digest(self):
        self.check_block("source_snapshot_unverified",
                         kwargs={"request_source_sha256": {"WORK.md": "b" * 64}})

    def test_changed_public_source_bytes(self):
        self.check_block("source_citation_unverified",
                         kwargs={"public_sources": {"WORK.md": SOURCE + "changed"}})

    def test_missing_source_line(self):
        self.check_block("source_citation_unverified",
                         finding={"source_line_start": 4, "source_line_end": 4})

    def test_boolean_line_rejected(self):
        self.check_block("source_lines_invalid",
                         finding={"source_line_start": True})

    def test_reversed_lines_rejected(self):
        self.check_block("source_lines_invalid",
                         finding={"source_line_start": 3, "source_line_end": 2})

    def test_source_range_over_twelve_rejected(self):
        self.check_block("source_lines_invalid",
                         finding={"source_line_start": 1, "source_line_end": 13})

    def test_wrong_target_revision(self):
        self.check_block("target_revision_unverified",
                         kwargs={"repo_file_sha256": {TARGET: "b" * 64}})

    def test_missing_target_revision(self):
        self.check_block("target_revision_unverified",
                         kwargs={"repo_file_sha256": {}})

    def test_target_path_traversal(self):
        self.check_block("unsafe_or_unscoped_target",
                         finding={"target_path": "tools/../private.py"})

    def test_source_path_traversal(self):
        self.check_block("unsafe_or_unscoped_target",
                         finding={"source_path": "../secret.md"})

    def test_target_not_code(self):
        self.check_block("unsafe_or_unscoped_target",
                         finding={"target_path": "tools/example_worker.md"})

    def test_test_path_outside_tests(self):
        self.check_block("unsafe_or_unscoped_target",
                         finding={"test_path": "scripts/run.sh"})

    def test_subsystem_missing(self):
        self.check_block("unsafe_or_unscoped_target",
                         finding={"subsystem": "none"})

    def test_generic_problem(self):
        self.check_block("non_actionable_finding",
                         finding={"problem": "Improve efficiency and explore options."})

    def test_generic_change(self):
        self.check_block("non_actionable_finding",
                         finding={"change": "TBD: improve the code in future research."})

    def test_empty_acceptance(self):
        self.check_block("non_actionable_finding",
                         finding={"acceptance": ""})

    def test_unapproved_role(self):
        self.check_block("finding_identity_invalid",
                         finding={"role": "walter"})

    def test_invalid_finding_key(self):
        self.check_block("finding_identity_invalid",
                         finding={"finding_key": "abc"})

    def test_invalid_change_type(self):
        self.check_block("finding_identity_invalid",
                         finding={"change_type": "shell-command"})

    def test_extra_model_supplied_field(self):
        finding, params = fixture()
        finding["run_command"] = "rm -rf /"
        with self.assertRaises(HandoffError) as error:
            propose(finding, **params)
        self.assertEqual(str(error.exception), "finding_schema_invalid")

    def test_duplicate_id_blocked(self):
        finding, params = fixture()
        candidate = propose(finding, **params)["candidate"]
        self.check_block("finding_already_recorded",
                         kwargs={"existing_tasks": [
                             {"id": candidate["id"], "status": "done", "scopes": []}]})

    def test_active_target_overlap(self):
        self.check_block("existing_task_scope_overlap",
                         kwargs={"existing_tasks": [
                             {"id": "other-task", "status": "active",
                              "scopes": [TARGET]}]})

    def test_blocked_test_overlap(self):
        self.check_block("existing_task_scope_overlap",
                         kwargs={"existing_tasks": [
                             {"id": "other-task", "status": "blocked",
                              "scopes": ["tests/test_example_worker.py"]}]})

    def test_ready_subsystem_overlap(self):
        self.check_block("existing_task_scope_overlap",
                         kwargs={"existing_tasks": [
                             {"id": "other-task", "status": "ready",
                              "scopes": ["subsystem:example-worker-regression"]}]})

    def test_done_scope_does_not_block_new_finding(self):
        finding, params = fixture()
        params["existing_tasks"] = [
            {"id": "older-done-task", "status": "done", "scopes": [TARGET]}]
        self.assertEqual(propose(finding, **params)["status"],
                         "reviewed_candidate_requires_separate_claim")

    def test_invalid_queue_shape(self):
        self.check_block("queue_snapshot_unverified",
                         kwargs={"existing_tasks": [{"id": "task", "status": "active"}]})

    def test_stable_identity_across_reworded_finding(self):
        finding, params = fixture()
        old = propose(finding, **params)["candidate"]["id"]
        finding["problem"] = (PROBLEM + " This is confirmed by the explicit "
                              "offline public evidence referenced above.")
        self.assertEqual(propose(finding, **params)["candidate"]["id"], old)

    def test_different_key_yields_distinct_identity(self):
        finding, params = fixture()
        old = propose(finding, **params)["candidate"]["id"]
        finding["finding_key"] = "worker-missing-receipt-second"
        params["review_receipt"]["finding_key"] = finding["finding_key"]
        self.assertNotEqual(propose(finding, **params)["candidate"]["id"], old)

    def test_no_private_error_echo(self):
        self.check_block("non_actionable_finding",
                         finding={"problem": "SECRET_PRIVATE_CLIENT_123"})
        self.assertNotIn("SECRET_PRIVATE", "non_actionable_finding")


if __name__ == "__main__":
    unittest.main()
