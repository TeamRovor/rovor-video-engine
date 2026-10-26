"""Synthetic 24-hour Mac worker evidence tests; never touches a real host."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_soak_evidence_gate import audit, DAY

START = 1800000000
END = START + DAY


def claim(name, at, role="gale", outcome="review_ready"):
    return {"job_id": name, "claimed_at": at, "role": role, "outcome": outcome}


def fixture():
    return {"heartbeats": list(range(START, END + 1, 300)),
            "claims": [claim("job-gale-001", START + 1000),
                       claim("job-mike-002", START + 2000, "mike", "model_failed")],
            "window_start": START, "window_end": END,
            "trusted_host_copy": True, "complete_event_ledger": True,
            "trusted_runtime_policy": True}


class SoakEvidenceTests(unittest.TestCase):
    def test_24h_coverage_is_attested_not_live_proof(self):
        result = audit(**fixture())
        self.assertEqual(result["status"], "source_only_evidence_consistent")
        self.assertEqual(result["heartbeat_coverage"], "24h_sample_coverage_attested")
        self.assertEqual(result["claim_safety"], "pacing_and_cap_consistent")
        self.assertFalse(result["host_authenticated_by_this_function"])
        self.assertFalse(result["model_inference_proven_by_this_function"])
        self.assertFalse(result["continuous_specialist_improvement_proven"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)

    def test_separate_specialist_outcomes(self):
        result = audit(**fixture())
        self.assertEqual(result["claims_24h"], 2)
        self.assertEqual(result["roles"]["gale"]["review_ready"], 1)
        self.assertEqual(result["roles"]["mike"]["model_failed"], 1)
        self.assertEqual(result["roles"]["jane"]["claims_24h"], 0)

    def test_no_claims_is_not_model_proof(self):
        data = fixture()
        data["claims"] = []
        result = audit(**data)
        self.assertEqual(result["heartbeat_coverage"], "24h_sample_coverage_attested")
        self.assertEqual(result["claims_24h"], 0)
        self.assertFalse(result["model_inference_proven_by_this_function"])

    def test_all_attestations_required(self):
        for field in ("trusted_host_copy", "complete_event_ledger",
                      "trusted_runtime_policy"):
            with self.subTest(field=field):
                data = fixture()
                data[field] = False
                self.assertEqual(audit(**data)["status"],
                                 "unverified_host_ledger_or_policy")

    def test_short_window_never_24h(self):
        data = fixture()
        data["window_end"] = START + DAY - 1
        data["heartbeats"] = data["heartbeats"][:-1]
        result = audit(**data)
        self.assertIn("heartbeat_window_short", result["issues"])
        self.assertEqual(result["heartbeat_coverage"], "insufficient")

    def test_more_than_one_day_window_rejected_instead_of_miscounted(self):
        data = fixture()
        data["window_end"] = END + 300
        data["heartbeats"].append(END + 300)
        self.assertEqual(audit(**data)["status"],
                         "invalid_window_or_pinned_policy")

    def test_missing_start_heartbeat(self):
        data = fixture()
        data["heartbeats"] = data["heartbeats"][4:]
        self.assertIn("heartbeat_start_missing", audit(**data)["issues"])

    def test_missing_end_heartbeat(self):
        data = fixture()
        data["heartbeats"] = data["heartbeats"][:-4]
        self.assertIn("heartbeat_end_missing", audit(**data)["issues"])

    def test_gap_over_nine_hundred(self):
        data = fixture()
        data["heartbeats"] = [x for x in data["heartbeats"]
                              if not START + 3000 <= x <= START + 3900]
        self.assertIn("heartbeat_gap_exceeded", audit(**data)["issues"])

    def test_gap_exactly_nine_hundred_allowed(self):
        data = fixture()
        data["heartbeats"] = [x for x in data["heartbeats"]
                              if x not in (START + 3000, START + 3300)]
        self.assertEqual(audit(**data)["heartbeat_coverage"],
                         "24h_sample_coverage_attested")

    def test_pacing_600_rejected(self):
        data = fixture()
        data["claims"][1]["claimed_at"] = START + 1600
        self.assertIn("claim_spacing_violation", audit(**data)["issues"])

    def test_pacing_601_allowed(self):
        data = fixture()
        data["claims"][1]["claimed_at"] = START + 1601
        self.assertEqual(audit(**data)["claim_safety"], "pacing_and_cap_consistent")

    def test_claims_are_sorted_without_mutating_input(self):
        data = fixture()
        data["claims"].reverse()
        before = copy.deepcopy(data)
        self.assertEqual(audit(**data)["claim_safety"], "pacing_and_cap_consistent")
        self.assertEqual(data, before)

    def test_rolling_limit_violation_with_lookback(self):
        data = fixture()
        data["rolling_claim_limit"] = 2
        data["claims"] = [claim("job-before", START - 500),
                          claim("job-one-01", START + 200),
                          claim("job-two-02", START + 900)]
        result = audit(**data)
        self.assertIn("rolling_claim_cap_exceeded", result["issues"])
        self.assertEqual(result["claims_24h"], 2)

    def test_rolling_boundary_excludes_exactly_one_day_old(self):
        data = fixture()
        data["rolling_claim_limit"] = 1
        data["claims"] = [claim("job-before", START - DAY + 1000),
                          claim("job-after1", START + 1000)]
        self.assertEqual(audit(**data)["claim_safety"], "pacing_and_cap_consistent")

    def test_duplicate_job_rejected(self):
        data = fixture()
        data["claims"].append(copy.deepcopy(data["claims"][0]))
        self.assertEqual(audit(**data)["status"], "invalid_or_duplicate_claim_evidence")

    def test_duplicate_heartbeat_rejected(self):
        data = fixture()
        data["heartbeats"].append(START)
        self.assertEqual(audit(**data)["status"], "duplicate_heartbeat_evidence")

    def test_unknown_role_or_outcome_rejected(self):
        for field, value in (("role", "walter"), ("outcome", "auto_approved"),
                             ("claimed_at", END + 1), ("job_id", "../secret")):
            with self.subTest(field=field):
                data = fixture()
                data["claims"][0][field] = value
                self.assertEqual(audit(**data)["status"],
                                 "invalid_or_duplicate_claim_evidence")

    def test_human_acceptance_requires_separate_attestation(self):
        data = fixture()
        data["claims"][0]["outcome"] = "review_accepted"
        self.assertEqual(audit(**data)["status"], "human_review_evidence_unverified")
        data["trusted_human_reviews"] = True
        result = audit(**data)
        self.assertEqual(result["roles"]["gale"]["human_accepted_attested"], 1)
        self.assertFalse(result["human_review_authenticated_by_this_function"])

    def test_invalid_pinned_policy_rejected(self):
        for field, value in (("rolling_claim_limit", 0),
                             ("min_claim_spacing_seconds", 0),
                             ("tick_seconds", 0),
                             ("allowed_gap_seconds", 200),
                             ("window_start", True)):
            with self.subTest(field=field):
                data = fixture()
                data[field] = value
                self.assertEqual(audit(**data)["status"],
                                 "invalid_window_or_pinned_policy")

    def test_malformed_heartbeat_rejected(self):
        data = fixture()
        data["heartbeats"][2] = "private path"
        self.assertEqual(audit(**data)["status"], "invalid_heartbeat_evidence")

    def test_bad_input_shape_rejected(self):
        data = fixture()
        data["claims"] = {"bad": "data"}
        self.assertEqual(audit(**data)["status"], "invalid_evidence_shape")

    def test_no_private_job_ids_or_timestamps_in_result(self):
        data = fixture()
        result = audit(**data)
        self.assertNotIn("job-gale-001", repr(result))
        self.assertNotIn(str(START), repr(result))
        self.assertNotIn("job-mike-002", repr(result))



def independent_fixture():
    data = fixture()
    data["independent_pool_mode"] = True
    data["trusted_pool_reservations"] = True
    data["pool_policy"] = {
        "pools": [
            {"pool_id": "account-a", "min_interval_seconds": 120,
             "max_claims_24h": 100},
            {"pool_id": "account-b", "min_interval_seconds": 120,
             "max_claims_24h": 100}],
        "models": [
            {"pool_id": pool, "model_id": model,
             "min_interval_seconds": 60, "max_claims_24h": 100}
            for pool in ("account-a", "account-b")
            for model in ("openrouter/fast:free", "groq/medium:free")]}
    for row, pool in zip(data["claims"], ("account-a", "account-b")):
        row["pool_id"] = pool
        row["model_id"] = "openrouter/fast:free"
    return data


class IndependentPoolSoakTests(unittest.TestCase):
    def test_same_second_independent_accounts_do_not_trigger_legacy_601s(self):
        data = independent_fixture()
        data["claims"][1]["claimed_at"] = data["claims"][0]["claimed_at"]
        result = audit(**data)
        self.assertEqual(result["status"], "source_only_evidence_consistent")
        self.assertEqual(result["claim_safety"], "pacing_and_cap_consistent")
        self.assertEqual(result["claims_24h"], 2)

    def test_same_account_same_second_is_pool_and_model_violation(self):
        data = independent_fixture()
        data["claims"][1]["pool_id"] = "account-a"
        data["claims"][1]["claimed_at"] = data["claims"][0]["claimed_at"]
        result = audit(**data)
        self.assertIn("pool_spacing_violation", result["issues"])
        self.assertIn("model_spacing_violation", result["issues"])
        self.assertEqual(result["claim_safety"], "violation")

    def test_two_models_same_account_still_share_pool_spacing(self):
        data = independent_fixture()
        data["claims"][1]["pool_id"] = "account-a"
        data["claims"][1]["model_id"] = "groq/medium:free"
        data["claims"][1]["claimed_at"] = data["claims"][0]["claimed_at"]
        result = audit(**data)
        self.assertIn("pool_spacing_violation", result["issues"])
        self.assertNotIn("model_spacing_violation", result["issues"])

    def test_same_model_two_accounts_have_independent_limits(self):
        data = independent_fixture()
        data["claims"][1]["claimed_at"] = data["claims"][0]["claimed_at"]
        self.assertEqual(audit(**data)["claim_safety"], "pacing_and_cap_consistent")

    def test_pool_rolling_cap_enforced_even_after_completion(self):
        data = independent_fixture()
        data["pool_policy"]["pools"][0]["max_claims_24h"] = 1
        data["claims"][1]["pool_id"] = "account-a"
        result = audit(**data)
        self.assertIn("pool_rolling_cap_exceeded", result["issues"])

    def test_model_rolling_cap_enforced_within_account(self):
        data = independent_fixture()
        data["pool_policy"]["models"][0]["max_claims_24h"] = 1
        data["claims"][1]["pool_id"] = "account-a"
        result = audit(**data)
        self.assertIn("model_rolling_cap_exceeded", result["issues"])

    def test_global_emergency_cap_remains_even_with_independent_pools(self):
        data = independent_fixture()
        data["claims"] = []
        for i in range(145):
            data["claims"].append({
                "job_id": "job-%04d" % i, "claimed_at": START + 1000 + i * 100,
                "role": "gale", "outcome": "model_failed",
                "pool_id": "account-a" if i % 2 == 0 else "account-b",
                "model_id": "openrouter/fast:free"})
        result = audit(**data)
        self.assertIn("rolling_claim_cap_exceeded", result["issues"])
        self.assertEqual(result["claims_24h"], 145)

    def test_model_interval_enforced_independently_of_pool_interval(self):
        data = independent_fixture()
        data["pool_policy"]["pools"][0]["min_interval_seconds"] = 1
        data["claims"][1]["pool_id"] = "account-a"
        data["claims"][1]["claimed_at"] = data["claims"][0]["claimed_at"] + 30
        result = audit(**data)
        self.assertIn("model_spacing_violation", result["issues"])
        self.assertNotIn("pool_spacing_violation", result["issues"])

    def test_unverified_reservations_fail_closed(self):
        data = independent_fixture()
        data["trusted_pool_reservations"] = False
        self.assertEqual(audit(**data)["status"],
                         "unverified_independent_pool_evidence")

    def test_incomplete_claim_to_pool_attribution_refused(self):
        data = independent_fixture()
        del data["claims"][0]["pool_id"]
        self.assertEqual(audit(**data)["status"],
                         "invalid_or_duplicate_claim_evidence")

    def test_unlisted_model_or_account_refused(self):
        for field, value in (("pool_id", "unlisted-account"),
                             ("model_id", "unlisted/model:free")):
            with self.subTest(field=field):
                data = independent_fixture()
                data["claims"][0][field] = value
                self.assertEqual(audit(**data)["status"],
                                 "invalid_or_incomplete_pool_claim_evidence")

    def test_duplicate_or_orphan_policy_rejected(self):
        data = independent_fixture()
        data["pool_policy"]["pools"].append(
            copy.deepcopy(data["pool_policy"]["pools"][0]))
        self.assertEqual(audit(**data)["status"], "invalid_pool_policy")
        data = independent_fixture()
        data["pool_policy"]["models"][0]["pool_id"] = "unlisted-account"
        self.assertEqual(audit(**data)["status"], "invalid_pool_policy")

    def test_boolean_and_zero_limits_rejected(self):
        for field, value in (("min_interval_seconds", True),
                             ("max_claims_24h", 0),
                             ("max_claims_24h", 145)):
            with self.subTest(field=field, value=value):
                data = independent_fixture()
                data["pool_policy"]["pools"][0][field] = value
                self.assertEqual(audit(**data)["status"], "invalid_pool_policy")

    def test_legacy_evidence_does_not_accept_pool_policy_injection(self):
        data = fixture()
        data["trusted_pool_reservations"] = True
        self.assertEqual(audit(**data)["status"], "unexpected_pool_evidence")

    def test_output_never_contains_private_pool_or_model_ids(self):
        data = independent_fixture()
        result = audit(**data)
        self.assertNotIn("account-a", repr(result))
        self.assertNotIn("openrouter/fast:free", repr(result))
        self.assertFalse(result["model_inference_proven_by_this_function"])


if __name__ == "__main__":
    unittest.main()
