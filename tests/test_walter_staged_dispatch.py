"""Offline end-to-end public workpack -> candidate -> free-only permit tests."""
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from omniroute_dispatch_permit import PermitError
from walter_research_backlog import validated
from walter_staged_dispatch import ProposalError, propose, SYSTEM

NOW = datetime(2026, 10, 24, 5, 0, tzinfo=timezone.utc)
M1 = "openrouter/cohere/north-mini-code:free"
M2 = "openrouter/nvidia/nemotron-3.5-super-vl:free"
ROUTE = "rovor-fast-free-v1"


def attestation(model):
    return {
        "model_id": model,
        "verified_at": NOW.isoformat(),
        "account_free_entitlement_verified": True,
        "provider_quota_verified": True,
        "public_research_privacy_approved": True,
        "cost_per_request_usd": 0,
        "cost_per_million_input_usd": 0,
        "cost_per_million_output_usd": 0,
        "other_fees_usd": 0,
        "remaining_requests": 2,
        "reasoning": {"mandatory": False, "supported_efforts": ["none"]},
    }


def valid(**changes):
    options = dict(
        root=ROOT, now=NOW, route=ROUTE, members=[M1, M2],
        catalog=[{"name": ROUTE, "strategy": "priority", "isHidden": False,
                  "models": [
                      {"kind": "model", "providerId": "openrouter", "model": M1},
                      {"kind": "model", "providerId": "openrouter", "model": M2}]}],
        attestations={M1: attestation(M1), M2: attestation(M2)},
        seen_dedupe=set(), reviewed_dedupe=set(),
        authoritative_ledger=True, authoritative_reviews=False,
        stop_present=False, owner_opt_in=True, other_job_running=False,
        rolling_claims=0)
    options.update(changes)
    return options


class StagedProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = validated(ROOT)["jobs"]
        cls.first = cls.jobs[0]
        cls.stage_one = {j["dedupe_key"] for j in cls.jobs if j["stage"] == 1}
        assert len(cls.stage_one) == 7

    def test_first_public_specialist_request_is_bounded_and_inert(self):
        result = propose(**valid())
        self.assertEqual(result["status"], "candidate_only_not_enqueued")
        self.assertEqual(result["candidate"]["id"], self.first["id"])
        self.assertEqual(result["candidate"]["stage"], 1)
        self.assertEqual(result["candidate"]["role"], "mike")
        self.assertEqual(result["candidate"]["dedupe_key"], self.first["dedupe_key"])
        self.assertEqual(result["request"]["model"], ROUTE)
        self.assertEqual(result["request"]["reasoning"], {"effort": "none"})
        self.assertEqual(result["request"]["max_tokens"], 2400)
        self.assertEqual(result["request"]["messages"][0]["content"], SYSTEM)
        self.assertIn("UNTRUSTED PUBLIC SOURCE", result["request"]["messages"][1]["content"])
        self.assertLessEqual(sum(len(m["content"]) for m in result["request"]["messages"]), 28000)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)
        self.assertFalse(result["mac_control_verified"])
        self.assertTrue(result["requires_atomic_sqlite_claim"])
        self.assertTrue(result["requires_private_receipt_review"])

    def test_source_fingerprints_are_actual_public_bytes(self):
        result = propose(**valid())
        for name, digest in result["candidate"]["public_source_sha256"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        self.assertEqual(len(result["candidate"]["packet_sha256"]), 64)

    def test_skips_previously_attempted_first_job_without_replay(self):
        result = propose(**valid(seen_dedupe={self.first["dedupe_key"]}))
        self.assertEqual(result["candidate"]["id"], self.jobs[1]["id"])
        self.assertEqual(result["candidate"]["role"], "jane")

    def test_stage_two_blocks_when_stage_one_has_no_review_proof(self):
        result = propose(**valid(seen_dedupe=self.stage_one))
        self.assertEqual(result["status"], "stage_two_requires_reviewed_stage_one")
        self.assertIsNone(result["candidate"])

    def test_stage_two_blocks_partial_or_untrusted_review_proof(self):
        partial = set(list(sorted(self.stage_one))[:-1])
        for reviewed, authoritative in ((partial, True), (self.stage_one, False),
                                        (None, True), ({"unseen"}, True)):
            with self.subTest(reviewed=reviewed, authoritative=authoritative):
                result = propose(**valid(seen_dedupe=self.stage_one,
                                         reviewed_dedupe=reviewed,
                                         authoritative_reviews=authoritative))
                self.assertEqual(result["status"], "stage_two_requires_reviewed_stage_one")

    def test_stage_two_eligible_only_after_seven_reviewed_receipts(self):
        result = propose(**valid(seen_dedupe=self.stage_one,
                                 reviewed_dedupe=self.stage_one,
                                 authoritative_reviews=True))
        self.assertEqual(result["candidate"]["stage"], 2)
        self.assertEqual(result["candidate"]["id"], self.jobs[7]["id"])

    def test_all_seen_exhausts_without_replay(self):
        all_seen = {job["dedupe_key"] for job in self.jobs}
        result = propose(**valid(seen_dedupe=all_seen,
                                 reviewed_dedupe=self.stage_one,
                                 authoritative_reviews=True))
        self.assertEqual(result, {"status": "exhausted_review_required", "candidate": None})

    def test_stop_blocks_before_any_workpack_read(self):
        with patch("walter_staged_dispatch.verify_checked_in",
                   side_effect=AssertionError("should not read")):
            result = propose(**valid(stop_present=True))
        self.assertEqual(result, {"status": "stopped", "candidate": None})

    def test_missing_ledger_approval_and_quota_block(self):
        for update in ({"authoritative_ledger": False}, {"owner_opt_in": False},
                       {"other_job_running": True}, {"rolling_claims": 5},
                       {"rolling_claims": None}, {"seen_dedupe": None},
                       {"seen_dedupe": {"ok", 123}}):
            with self.subTest(update=update):
                result = propose(**valid(**update))
                self.assertEqual(result["status"], "ledger_or_authorization_unverified")

    def test_stale_provider_attestation_fails_closed(self):
        data = valid()
        data["attestations"][M1]["verified_at"] = "2026-10-23T00:00:00Z"
        with self.assertRaises(PermitError) as caught:
            propose(**data)
        self.assertEqual(str(caught.exception), "provider_evidence_stale_or_future")

    def test_paid_fallback_fails_closed(self):
        data = valid()
        data["catalog"][0]["models"][1]["model"] = "openrouter/vendor/paid"
        with self.assertRaises(PermitError):
            propose(**data)

    def test_drifted_checked_in_packet_fails_before_proposal(self):
        with patch("walter_staged_dispatch.verify_checked_in",
                   side_effect=ValueError("checked_in_workpack_drift")):
            with self.assertRaisesRegex(ValueError, "checked_in_workpack_drift"):
                propose(**valid())

    def test_oversized_source_prompt_fails_closed(self):
        with patch("walter_staged_dispatch._source", return_value="X" * 19000):
            with self.assertRaises(ProposalError) as caught:
                propose(**valid())
        self.assertEqual(str(caught.exception), "public_prompt_exceeds_limit")

    def test_input_is_unchanged(self):
        args = valid()
        before = copy.deepcopy(args)
        propose(**args)
        self.assertEqual(args, before)


if __name__ == "__main__":
    unittest.main()
