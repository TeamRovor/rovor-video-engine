"""Offline proportional model-routing tests. No gateway or worker calls."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_capacity_router as policy

NOW = 100000.0

def task(**changes):
    data = {
        "id": "rovor_test_001", "public_only": True, "minimum_tier": 1,
        "required_skills": ["text"], "estimated_input_tokens": 1000,
        "requested_output_tokens": 200,
    }
    data.update(changes)
    return data

def model(name="openrouter/provider/fast:free", **changes):
    data = {
        "model_id": name, "tier": 1, "max_input_tokens": 8192,
        "max_output_tokens": 2048, "max_inflight": 2, "inflight": 0,
        "remaining_requests": 100, "latency_ms": 200,
        "claims_since_reset": 4, "skills": ["text", "code"],
        "health": "ready", "success_fraction": 0.99,
        "verified_at": NOW - 60, "quota_reset_at": NOW + 3600,
        "cooldown_until": None, "account_free_verified": True,
        "privacy_approved": True, "terms_approved": True,
        "quota_verified": True, "approved_model_id": True,
        "completed_canary_verified": True, "cost_per_request_usd": 0,
    }
    data.update(changes)
    return data


class CapacityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fast = model()
        self.deep = model("gemini/provider/reasoning:free", tier=3,
                          max_input_tokens=100000, max_output_tokens=10000,
                          skills=["text", "code", "reasoning", "long_context"],
                          latency_ms=650)
        self.middle = model("groq/provider/medium:free", tier=2,
                            max_input_tokens=16000, max_output_tokens=4000,
                            skills=["text", "code", "reasoning"],
                            success_fraction=0.95)

    def decide(self, jobs=None, models=None, **flags):
        return policy.decide(jobs if jobs is not None else task(),
                             models if models is not None else
                             [self.fast, self.middle, self.deep],
                             now=NOW, **flags)

    def test_small_task_chooses_light_model_not_strongest(self):
        x = self.decide()
        self.assertEqual(x["status"], "candidate_only")
        self.assertEqual(x["chosen_model_id"], self.fast["model_id"])
        self.assertEqual(x["allowed_inference_posts"], 0)
        self.assertFalse(x["authorized_to_claim"])

    def test_reasoning_task_avoids_weak_model(self):
        job = task(minimum_tier=2, required_skills=["reasoning"],
                   estimated_input_tokens=1200)
        x = self.decide(jobs=job)
        self.assertEqual(x["chosen_model_id"], self.middle["model_id"])

    def test_large_input_routes_only_to_capable_model(self):
        job = task(minimum_tier=2, required_skills=["long_context"],
                   estimated_input_tokens=30000, requested_output_tokens=3000)
        self.assertEqual(self.decide(jobs=job)["chosen_model_id"], self.deep["model_id"])

    def test_oversized_work_must_be_split_no_silent_overload(self):
        job = task(estimated_input_tokens=180000,
                   requested_output_tokens=25000)
        x = self.decide(jobs=job)
        self.assertEqual(x["status"], "needs_task_split_or_more_capable_model")
        self.assertIsNone(x["chosen_model_id"])

    def test_full_model_is_immediately_replaced_by_capable_alternative(self):
        self.fast["inflight"] = self.fast["max_inflight"]
        x = self.decide()
        self.assertEqual(x["chosen_model_id"], self.middle["model_id"])
        self.assertEqual(x["current_model_health"][self.fast["model_id"]],
                         "concurrency_full")

    def test_used_up_quota_uses_alternative_and_reports_reset(self):
        self.fast["remaining_requests"] = 0
        x = self.decide()
        self.assertEqual(x["chosen_model_id"], self.middle["model_id"])
        self.assertEqual(x["current_model_health"][self.fast["model_id"]],
                         "provider_quota_exhausted")
        x = self.decide(models=[self.fast])
        self.assertEqual(x["status"], "wait_for_fresh_capacity")
        self.assertEqual(x["next_reevaluate_at"], NOW + 3600)

    def test_reset_time_not_equal_fresh_quota_evidence(self):
        self.fast["remaining_requests"] = 0
        self.fast["quota_reset_at"] = NOW - 1
        x = self.decide(models=[self.fast])
        self.assertIsNone(x["chosen_model_id"])
        self.assertTrue(x["requires_fresh_quota_snapshot"])
        self.fast["remaining_requests"] = 1
        self.fast["verified_at"] = NOW - 1000
        x = self.decide(models=[self.fast])
        self.assertEqual(x["reason"], "no_currently_verified_and_available_model")
        self.fast["verified_at"] = NOW
        self.assertEqual(self.decide(models=[self.fast])["chosen_model_id"],
                         self.fast["model_id"])

    def test_cooldown_and_unhealthy_model_get_safe_fallback(self):
        self.fast["cooldown_until"] = NOW + 200
        self.assertEqual(self.decide()["chosen_model_id"], self.middle["model_id"])
        x = self.decide(models=[self.fast])
        self.assertEqual(x["status"], "wait_for_fresh_capacity")
        self.assertEqual(x["next_reevaluate_at"], NOW + 200)
        self.fast["health"] = "down"
        self.assertEqual(self.decide(models=[self.fast])["status"], "blocked")

    def test_no_paid_or_unverified_model_dispatch(self):
        for update in (
            {"cost_per_request_usd": 0.0001},
            {"account_free_verified": False},
            {"privacy_approved": False},
            {"terms_approved": False},
            {"quota_verified": False},
            {"approved_model_id": False},
            {"completed_canary_verified": False},
            {"verified_at": NOW - 901},
        ):
            with self.subTest(update=update):
                a = model(**update)
                x = self.decide(models=[a])
                self.assertEqual(x["status"], "blocked")
                self.assertIsNone(x["chosen_model_id"])

    def test_stop_and_failure_circuit_never_bypassed_by_fallback(self):
        self.assertEqual(self.decide(stop_requested=True)["reason"], "stop_requested")
        self.assertEqual(self.decide(failure_circuit_open=True)["reason"],
                         "global_failure_circuit_open")
        self.assertIsNone(self.decide(stop_requested=True)["chosen_model_id"])

    def test_quality_preferred_for_equal_tier_before_latency(self):
        two = model("openrouter/provider/second:free", latency_ms=2, success_fraction=0.60)
        result = self.decide(models=[self.fast, two])
        self.assertEqual(result["chosen_model_id"], self.fast["model_id"])

    def test_duplicate_ids_or_corrupt_attestations_fail_closed(self):
        with self.assertRaisesRegex(policy.AdmissionError, "duplicate_model_resource"):
            self.decide(models=[self.fast, copy.deepcopy(self.fast)])
        with self.assertRaisesRegex(policy.AdmissionError, "slot_attestation_invalid"):
            self.decide(models=[model(account_free_verified="yes")])
        with self.assertRaisesRegex(policy.AdmissionError, "slot_capacity_invalid"):
            self.decide(models=[model(inflight=3)])
        with self.assertRaisesRegex(policy.AdmissionError, "slot_reset_invalid"):
            self.decide(models=[model(quota_reset_at="tomorrow")])

    def test_private_client_job_never_dispatched_on_free_model(self):
        with self.assertRaisesRegex(policy.AdmissionError, "task_invalid_or_not_public"):
            self.decide(jobs=task(public_only=False))

    def test_no_resource_and_no_skill_fit_are_explicit(self):
        self.assertEqual(self.decide(models=[])["status"], "needs_task_split_or_more_capable_model")
        self.assertEqual(self.decide(jobs=task(required_skills=["vision"]))["status"],
                         "needs_task_split_or_more_capable_model")

    def test_headroom_prevents_just_barely_fitting_tasks(self):
        limit = int(self.fast["max_input_tokens"] * policy.INPUT_HEADROOM)
        okay = task(estimated_input_tokens=limit)
        self.assertEqual(self.decide(jobs=okay, models=[self.fast])["status"], "candidate_only")
        too_big = task(estimated_input_tokens=limit+1)
        self.assertEqual(self.decide(jobs=too_big, models=[self.fast])["status"],
                         "needs_task_split_or_more_capable_model")

    def test_does_not_mutate_task_or_catalog(self):
        items = [self.fast, self.middle]
        orig = copy.deepcopy(items)
        job = task()
        job_before = copy.deepcopy(job)
        self.decide(jobs=job, models=items)
        self.assertEqual(items, orig)
        self.assertEqual(job, job_before)

if __name__ == "__main__":
    unittest.main()
