"""Synthetic Mac SQLite fixtures only: no private host receipts."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_real_receipt_bridge import BridgeError, normalize_dedupe, prepare

NOW = 1800000000
JOB = "123e4567-e89b-12d3-a456-426614174000"
SHA = "a" * 64


def fixture():
    jobs = [{"id": JOB, "kind": "research.omniroute", "dedupe_key": SHA,
             "status": "needs_review", "updated_at": NOW - 40.2,
             "result": json.dumps({"role": "gale", "draft_status": "draft_completed_needs_review",
                                   "review_status": "draft_ready_for_human_review",
                                   "receipt": "/Users/private/SECRET-RECEIPT",
                                   "raw_model_text": "SECRET-PRIVATE-MODEL-DRAFT"})}]
    claims = [{"job_id": JOB, "event": "claimed", "timestamp": NOW - 100.5}]
    roles = {JOB: "gale"}
    reviews = []
    candidates = [{"role": "mike", "task_id": "mike-pending-fix",
                   "dedupe_key": "b" * 64, "source_sha256": "c" * 64,
                   "priority": 1}]
    flags = dict(trusted_sqlite_copy=True, trusted_role_mapping=True,
                 trusted_human_reviews=True, complete_ledger=True,
                 trusted_grounded_candidates=True)
    return [jobs, claims, roles, reviews, candidates, flags]


def run(parts=None):
    jobs, claims, roles, reviews, candidates, flags = fixture() if parts is None else parts
    return prepare(jobs, claims, roles, reviews, candidates, now=NOW, **flags)


class ReceiptBridgeTests(unittest.TestCase):
    def blocked(self, code, mutate):
        parts = fixture()
        mutate(parts)
        with self.assertRaises(BridgeError) as error:
            run(parts)
        self.assertEqual(str(error.exception), code)

    def test_real_uuid_and_sha_dedupe_normalized(self):
        result = run()
        self.assertEqual(result["outcomes"][0]["job_id"], "job-" + JOB.replace("-", ""))
        self.assertEqual(result["outcomes"][0]["dedupe_key"], "sha-" + SHA)
        self.assertEqual(result["candidates"][0]["dedupe_key"], "sha-" + "b" * 64)
        self.assertEqual(result["outcomes"][0]["status"], "review_ready")
        self.assertIn("sha-" + SHA, result["seen_dedupe"])

    def test_private_content_never_emitted(self):
        output = repr(run())
        for secret in ("SECRET-RECEIPT", "SECRET-PRIVATE-MODEL-DRAFT", "/Users/private"):
            self.assertNotIn(secret, output)
        self.assertEqual(run()["model_calls"], 0)
        self.assertEqual(run()["queue_writes"], 0)
        self.assertFalse(run()["mac_execution"])

    def test_human_acceptance_requires_separate_record(self):
        parts = fixture()
        parts[3].append({"job_id": JOB, "decision": "accepted", "decided_at": NOW - 10})
        self.assertEqual(run(parts)["outcomes"][0]["status"], "review_accepted")
        parts[3][0]["decision"] = "rejected"
        self.assertEqual(run(parts)["outcomes"][0]["status"], "review_rejected")

    def test_model_cannot_self_approve(self):
        parts = fixture()
        data = json.loads(parts[0][0]["result"])
        data["review_status"] = "human_approved"
        parts[0][0]["result"] = json.dumps(data)
        self.assertEqual(run(parts)["outcomes"][0]["status"], "pending_review")

    def test_fails_without_independent_trust(self):
        for flag in fixture()[5]:
            self.blocked("independent_evidence_required",
                         lambda p, flag=flag: p[5].update({flag: False}))

    def test_duplicate_job_rejected(self):
        self.blocked("duplicate_or_unsafe_private_job",
                     lambda p: p[0].append(copy.deepcopy(p[0][0])))

    def test_duplicate_dedupe_rejected(self):
        def change(p):
            other = copy.deepcopy(p[0][0])
            other["id"] = "223e4567-e89b-12d3-a456-426614174000"
            p[0].append(other)
        self.blocked("duplicate_or_unsafe_private_job", change)

    def test_duplicate_claim_rejected(self):
        self.blocked("duplicate_or_unmatched_claim", lambda p: p[1].append(dict(p[1][0])))

    def test_missing_claim_rejected(self):
        self.blocked("missing_or_replayed_claim", lambda p: p[1].clear())

    def test_queued_unclaimed_job_remains_seen(self):
        parts = fixture()
        parts[0][0]["status"] = "queued"
        parts[0][0]["result"] = None
        parts[1].clear()
        parts[2].clear()
        result = run(parts)
        self.assertEqual(result["outcomes"], [])
        self.assertIn("sha-" + SHA, result["seen_dedupe"])

    def test_claimed_job_cannot_return_to_queued(self):
        self.blocked("missing_or_replayed_claim", lambda p: p[0][0].update(status="queued"))

    def test_failed_job_is_not_review_ready(self):
        parts = fixture()
        parts[0][0]["status"] = "failed"
        self.assertEqual(run(parts)["outcomes"][0]["status"], "model_failed")

    def test_no_auto_retry_receipt_is_failed(self):
        parts = fixture()
        parts[0][0]["result"] = json.dumps({"draft_status": "needs_review_no_auto_retry"})
        self.assertEqual(run(parts)["outcomes"][0]["status"], "model_failed")

    def test_unknown_review_cannot_approve(self):
        self.blocked("invalid_independent_review",
                     lambda p: p[3].append({"job_id": "unknown", "decision": "accepted",
                                            "decided_at": NOW - 10}))

    def test_review_cannot_precede_job(self):
        self.blocked("review_without_completed_draft",
                     lambda p: p[3].append({"job_id": JOB, "decision": "accepted",
                                            "decided_at": NOW - 80}))

    def test_model_failure_cannot_be_human_accepted(self):
        def change(p):
            p[0][0]["status"] = "failed"
            p[3].append({"job_id": JOB, "decision": "accepted", "decided_at": NOW - 10})
        self.blocked("review_without_completed_draft", change)

    def test_missing_role_mapping_refused(self):
        self.blocked("unverified_job_role_mapping", lambda p: p[2].clear())

    def test_claim_timestamp_after_job_refused(self):
        self.blocked("invalid_private_timeline", lambda p: p[1][0].update(timestamp=NOW - 1))

    def test_bad_json_never_exposes_private_content(self):
        self.blocked("invalid_private_result", lambda p: p[0][0].update(result="SECRET {"))

    def test_bad_job_kind_rejected(self):
        self.blocked("duplicate_or_unsafe_private_job",
                     lambda p: p[0][0].update(kind="terminal.probe"))

    def test_malformed_claim_id_fails_closed(self):
        self.blocked("duplicate_or_unmatched_claim",
                     lambda p: p[1][0].update(job_id=[]))

    def test_malformed_review_id_fails_closed(self):
        self.blocked("invalid_independent_review",
                     lambda p: p[3].append({"job_id": [], "decision": "accepted",
                                            "decided_at": NOW - 10}))

    def test_extreme_timestamp_fails_closed(self):
        self.blocked("invalid_private_timestamp",
                     lambda p: p[1][0].update(timestamp=10 ** 1000))

    def test_bogus_uuid_rejected(self):
        self.blocked("invalid_private_job_id", lambda p: p[0][0].update(id="../../private"))

    def test_rejects_invalid_dedupe(self):
        with self.assertRaises(BridgeError):
            normalize_dedupe("../../private")

    def test_existing_coverage_selector_accepts_normalized_receipts(self):
        from walter_specialist_coverage import choose
        output = run()
        decision = choose(output["candidates"], output["outcomes"], now=NOW,
                          seen_dedupe=output["seen_dedupe"],
                          trusted_candidates=True, trusted_outcomes=True,
                          authoritative_ledger=True, stop_present=False,
                          other_job_running=False, owner_opt_in=True)
        self.assertEqual(decision["candidate"]["role"], "mike")
        self.assertEqual(decision["coverage"]["gale"]["awaiting_review"], 1)

    def test_existing_coverage_selector_blocks_pending_global_review(self):
        from walter_specialist_coverage import choose
        parts = fixture()
        for i in range(1, 7):
            row = copy.deepcopy(parts[0][0])
            row["id"] = f"{i:08x}-e89b-12d3-a456-426614174000"
            row["dedupe_key"] = f"{i:064x}"
            parts[0].append(row)
            parts[1].append({"job_id": row["id"], "event": "claimed",
                             "timestamp": NOW - 100})
            parts[2][row["id"]] = "gale"
        output = run(parts)
        decision = choose(output["candidates"], output["outcomes"], now=NOW,
                          seen_dedupe=output["seen_dedupe"],
                          trusted_candidates=True, trusted_outcomes=True,
                          authoritative_ledger=True, stop_present=False,
                          other_job_running=False, owner_opt_in=True)
        self.assertEqual(decision["status"], "global_review_backpressure")


if __name__ == "__main__":
    unittest.main()
