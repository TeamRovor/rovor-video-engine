"""Offline regression: no provider calls, no Mac access, no new queue."""
from datetime import datetime, timedelta, timezone
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from omniroute_dispatch_permit import (
    PermitError, build_candidate_request, MAX_EVIDENCE_AGE_SECONDS,
)
from omniroute_reasoning_admission import AdmissionError

NOW = datetime(2026, 10, 24, 4, 0, tzinfo=timezone.utc)
M1 = "openrouter/cohere/north-mini-code:free"
M2 = "openrouter/nvidia/nemotron-3.5-super-vl:free"
ROUTE = "rovor-fast-free-v1"
KEY = "walter-public-v1-mac-worker-stop-recovery"


def entry(model):
    return {"kind": "model", "providerId": "openrouter", "model": model}


def attestation(model):
    return {
        "model_id": model,
        "verified_at": NOW.isoformat(),
        "account_free_entitlement_verified": True,
        "provider_quota_verified": True,
        "public_research_privacy_approved": True,
        "cost_per_request_usd": 0,
        "cost_per_million_input_usd": 0.0,
        "cost_per_million_output_usd": 0,
        "other_fees_usd": 0,
        "remaining_requests": 2,
        "reasoning": {"mandatory": False, "supported_efforts": ["none", "low"]},
    }


def valid():
    return dict(
        route=ROUTE, members=(M1, M2),
        catalog=[{"name": ROUTE, "strategy": "priority", "isHidden": False,
                  "models": [entry(M1), entry(M2)]}],
        attestations={M1: attestation(M1), M2: attestation(M2)},
        messages=[{"role": "system", "content": "Public only"},
                  {"role": "user", "content": "Review the public workpack"}],
        now=NOW, stop_present=False, owner_opt_in=True,
        public_sources_verified=True, authoritative_ledger=True,
        dedupe_key=KEY, seen_dedupe=set(), rolling_claims=0,
        other_job_running=False,
    )


class PermitTests(unittest.TestCase):
    def deny(self, code, **changes):
        args = valid()
        args.update(changes)
        with self.assertRaises(PermitError) as ctx:
            build_candidate_request(**args)
        self.assertEqual(str(ctx.exception), code)

    def test_valid_candidate_is_inert_and_bounded(self):
        result = build_candidate_request(**valid())
        self.assertEqual(result["status"], "eligible_candidate_only")
        self.assertFalse(result["automatic_dispatch_authorized"])
        self.assertTrue(result["requires_atomic_sqlite_claim"])
        self.assertTrue(result["requires_private_receipt_review"])
        self.assertEqual(result["checked_model_count"], 2)
        self.assertEqual(result["request"]["reasoning"], {"effort": "none"})
        self.assertEqual(result["request"]["max_tokens"], 2400)
        self.assertEqual(result["request"]["model"], ROUTE)

    def test_input_not_mutated(self):
        data = valid()
        original = copy.deepcopy(data)
        build_candidate_request(**data)
        self.assertEqual(data, original)

    def test_stop_present_or_unknown(self):
        for value in (True, None, 0, "false"):
            self.deny("stop_or_unknown", stop_present=value)

    def test_owner_opt_in_explicit(self):
        for value in (False, None, 1, "yes"):
            self.deny("model_use_not_authorized", owner_opt_in=value)

    def test_only_public_sources(self):
        for value in (False, None, 1):
            self.deny("private_or_unverified_source", public_sources_verified=value)

    def test_ledger_required(self):
        for field, value in (
            ("authoritative_ledger", False), ("authoritative_ledger", 1),
            ("other_job_running", True), ("other_job_running", None),
            ("seen_dedupe", None), ("seen_dedupe", ["old"]),
            ("seen_dedupe", {42}), ("dedupe_key", "bad key"),
            ("dedupe_key", ""), ("rolling_claims", None),
            ("rolling_claims", True), ("rolling_claims", -1),
            ("rolling_claims", 5), ("rolling_claims", 20),
        ):
            with self.subTest(field=field, value=str(value)):
                self.deny("ledger_or_budget_unverified", **{field: value})

    def test_fifth_claim_allowed_but_sixth_blocked(self):
        result = build_candidate_request(**{**valid(), "rolling_claims": 4})
        self.assertEqual(result["status"], "eligible_candidate_only")
        self.deny("ledger_or_budget_unverified", rolling_claims=5)

    def test_failed_or_successful_dedupe_never_replayed(self):
        self.deny("previous_attempt_no_replay", seen_dedupe={KEY})

    def test_timezone_aware_now_required(self):
        self.deny("clock_unverified", now=NOW.replace(tzinfo=None))
        self.deny("clock_unverified", now="2026-10-24")

    def test_missing_or_duplicate_combo(self):
        self.deny("combo_missing_or_ambiguous", catalog=[])
        self.deny("combo_missing_or_ambiguous",
                  catalog=valid()["catalog"] * 2)
        self.deny("combo_catalog_unverified", catalog=None)

    def test_combo_strategy_or_hidden_drift(self):
        for field, value in (("strategy", "round_robin"), ("isHidden", True),
                             ("isHidden", None)):
            c = copy.deepcopy(valid()["catalog"])
            c[0][field] = value
            self.deny("combo_policy_changed", catalog=c)

    def test_combo_membership_order_is_pinned(self):
        c = copy.deepcopy(valid()["catalog"])
        c[0]["models"].reverse()
        self.deny("combo_members_changed", catalog=c)

    def test_combo_rejects_nonfree_fallback(self):
        for change in (
            {"model": "openrouter/vendor/paid"},
            {"kind": "combo"}, {"providerId": "unknown"},
            {"model": None},
        ):
            c = copy.deepcopy(valid()["catalog"])
            c[0]["models"][1].update(change)
            self.deny("combo_nonfree_fallback", catalog=c)

    def test_expected_route_members_are_not_guessed(self):
        self.deny("invalid_route_identity", members=[M1, M1])
        self.deny("invalid_route_identity", members=[])
        self.deny("invalid_route_identity", route="model/auto")

    def test_missing_or_extra_attestation(self):
        self.deny("provider_evidence_incomplete", attestations={M1: attestation(M1)})
        e = copy.deepcopy(valid()["attestations"])
        e["openrouter/extra:free"] = attestation("openrouter/extra:free")
        self.deny("provider_evidence_incomplete", attestations=e)

    def test_attestation_exact_model_binding(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M2]["model_id"] = M1
        self.deny("provider_model_mismatch", attestations=e)

    def test_billing_and_privacy_evidence_required(self):
        for field in ("account_free_entitlement_verified",
                      "provider_quota_verified",
                      "public_research_privacy_approved"):
            for value in (None, False, 1):
                e = copy.deepcopy(valid()["attestations"])
                e[M1][field] = value
                with self.subTest(field=field, value=value):
                    self.deny("provider_eligibility_unverified", attestations=e)

    def test_zero_price_is_required_for_every_cost_field(self):
        for field in ("cost_per_request_usd", "cost_per_million_input_usd",
                      "cost_per_million_output_usd", "other_fees_usd"):
            for value in (None, 0.01, -1, True, float("nan")):
                e = copy.deepcopy(valid()["attestations"])
                e[M2][field] = value
                with self.subTest(field=field, value=str(value)):
                    self.deny("zero_cost_unverified", attestations=e)

    def test_no_verified_provider_quota(self):
        for value in (0, -1, None, True, 0.5):
            e = copy.deepcopy(valid()["attestations"])
            e[M2]["remaining_requests"] = value
            self.deny("provider_quota_exhausted", attestations=e)

    def test_stale_evidence(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M1]["verified_at"] = (NOW - timedelta(
            seconds=MAX_EVIDENCE_AGE_SECONDS + 1)).isoformat()
        self.deny("provider_evidence_stale_or_future", attestations=e)

    def test_freshness_boundary(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M1]["verified_at"] = (NOW - timedelta(
            seconds=MAX_EVIDENCE_AGE_SECONDS)).isoformat()
        self.assertEqual(build_candidate_request(**{
            **valid(), "attestations": e})["status"], "eligible_candidate_only")

    def test_future_evidence_rejected(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M2]["verified_at"] = (NOW + timedelta(seconds=31)).isoformat()
        self.deny("provider_evidence_stale_or_future", attestations=e)

    def test_invalid_evidence_timestamp(self):
        for value in ("2026-10-24", "not-a-date", None, 123):
            e = copy.deepcopy(valid()["attestations"])
            e[M2]["verified_at"] = value
            self.deny("evidence_timestamp_invalid", attestations=e)

    def test_reasoning_mandatory_fails_closed(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M1]["reasoning"]["mandatory"] = True
        with self.assertRaises(AdmissionError) as ctx:
            build_candidate_request(**{**valid(), "attestations": e})
        self.assertEqual(str(ctx.exception), "reasoning_may_be_mandatory")

    def test_reasoning_none_missing_fails_closed(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M1]["reasoning"]["supported_efforts"] = ["low", "high"]
        with self.assertRaises(AdmissionError) as ctx:
            build_candidate_request(**{**valid(), "attestations": e})
        self.assertEqual(str(ctx.exception), "reasoning_disable_unsupported")

    def test_unknown_reasoning_fails_closed(self):
        e = copy.deepcopy(valid()["attestations"])
        e[M1]["reasoning"] = None
        self.deny("reasoning_capabilities_unverified", attestations=e)

    def test_untrusted_prompt_is_rejected_downstream(self):
        args = valid()
        args["messages"][1]["content"] = ""
        with self.assertRaises(AdmissionError):
            build_candidate_request(**args)

    def test_errors_never_echo_private_provider_data(self):
        args = valid()
        args["attestations"][M1]["verified_at"] = "PRIVATE_SECRET_123"
        with self.assertRaises(PermitError) as ctx:
            build_candidate_request(**args)
        self.assertNotIn("PRIVATE_SECRET_123", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
