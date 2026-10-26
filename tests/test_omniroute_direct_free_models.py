"""Direct-provider entitlement/route checks; zero outbound model calls."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import omniroute_fleet_binding as binding
from omniroute_capacity_router import MODEL_ID


class DirectFreeModelTests(unittest.TestCase):
    NOW = 1000

    def combo(self, provider, model):
        return [{"name": "rovor-" + provider + "-single",
                 "strategy": "priority", "isHidden": False,
                 "models": [{"kind": "model", "providerId": provider,
                             "model": model}]}]

    def entitlement(self, model, pool="groq-main"):
        return {
            "model_id": model, "quota_pool_id": pool,
            "verified_at": self.NOW - 2,
            "pool_verified_at": self.NOW - 2,
            "cost_per_request_usd": 0,
            "account_free_verified": True,
            "quota_verified": True,
            "approved_model_id": True,
            "completed_canary_verified": True,
            "privacy_approved": True,
            "terms_approved": True,
            "commercial_use_permitted": True,
            "no_billable_fallback_verified": True
        }

    def assert_bound(self, provider, model, pool):
        catalog = self.combo(provider, model)
        routes = {model: {"combo": catalog[0]["name"], "provider_id": provider}}
        evidence = self.entitlement(model, pool)
        combo = binding.verify_binding(model, routes, catalog,
                        verified_slot=evidence, pool_id=pool, now=self.NOW)
        self.assertEqual(combo, catalog[0]["name"])
        receipt = {"model_id": model, "pool_id": pool,
                   "provider_id": provider, "combo": combo,
                   "zero_cost_witness": binding.zero_cost_witness(
                       evidence, model, provider, pool, now=self.NOW)}
        self.assertEqual(binding.verify_before_completion(
                         receipt, catalog, now=self.NOW), combo)

    def test_non_suffix_models_from_three_direct_providers(self):
        for provider, model, pool in [
            ("groq", "groq/openai/gpt-oss-20b", "groq-main"),
            ("cloudflare-ai", "cloudflare-ai/@cf/meta/llama-3.2-3b-instruct",
             "cloudflare-main"),
            ("sambanova", "sambanova/DeepSeek-V3.2", "sambanova-main"),
            ("huggingface", "huggingface/Qwen/Qwen3.5-9B", "huggingface-main"),
        ]:
            with self.subTest(provider=provider):
                self.assertIsNotNone(MODEL_ID.fullmatch(model))
                self.assert_bound(provider, model, pool)

    def test_missing_free_entitlement_fails_closed(self):
        model = "groq/openai/gpt-oss-20b"
        catalog = self.combo("groq", model)
        routes = {model: {"combo": catalog[0]["name"], "provider_id": "groq"}}
        with self.assertRaisesRegex(ValueError, "zero_cost|identity"):
            binding.verify_binding(model, routes, catalog,
                                   pool_id="groq-main", now=self.NOW)

    def test_paid_or_stale_or_unapproved_commercial_direct_model_rejected(self):
        model = "groq/openai/gpt-oss-20b"
        for field, value in [
            ("cost_per_request_usd", 0.001),
            ("commercial_use_permitted", False),
            ("no_billable_fallback_verified", False),
            ("account_free_verified", False),
            ("terms_approved", False),
            ("completed_canary_verified", False),
            ("verified_at", self.NOW - 901),
            ("pool_verified_at", self.NOW - 901),
            ("quota_pool_id", "other-account"),
        ]:
            with self.subTest(field=field):
                slot = self.entitlement(model)
                slot[field] = value
                with self.assertRaises(ValueError):
                    binding.zero_cost_witness(
                        slot, model, "groq", "groq-main", now=self.NOW)

    def test_provider_and_fallback_drift_rejected_before_completion(self):
        model = "groq/openai/gpt-oss-20b"
        witness = self.entitlement(model)
        receipt = {"model_id": model, "pool_id": "groq-main",
                   "combo": "rovor-groq-single", "provider_id": "groq",
                   "zero_cost_witness": witness}
        good = self.combo("groq", model)
        for invalid in (
            [{"name": "rovor-groq-single", "strategy": "priority",
              "isHidden": False, "models": [
                  good[0]["models"][0], good[0]["models"][0]]}],
            [{"name": "rovor-groq-single", "strategy": "priority",
              "isHidden": False, "models": [{
                  "kind": "model", "providerId": "openrouter",
                  "model": model}]}],
        ):
            with self.assertRaises(ValueError):
                binding.verify_before_completion(
                    receipt, invalid, now=self.NOW)
        self.assertEqual(binding.verify_before_completion(
            receipt, good, now=self.NOW), "rovor-groq-single")

    def test_existing_explicit_free_route_still_works(self):
        model = "openrouter/cohere/north-mini-code:free"
        catalog = self.combo("openrouter", model)
        routes = {model: {"combo": "rovor-openrouter-single",
                          "provider_id": "openrouter"}}
        self.assertEqual(binding.verify_binding(
            model, routes, catalog), "rovor-openrouter-single")


if __name__ == "__main__":
    unittest.main()
