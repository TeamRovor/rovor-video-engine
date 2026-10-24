"""Offline invariants for ROVOR provider-routing intent (no API calls)."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/"coordination/ghost-provider-policy.json").read_text())
ROLE=json.loads((ROOT/"coordination/ghost-role-bootstrap.json").read_text())
ARCH=(ROOT/"architecture/HYBRID-24-7-GHOST-WORKFORCE.md").read_text()


class HybridProviderPolicyTests(unittest.TestCase):
    def test_scope_and_deployment_are_honest(self):
        self.assertEqual(POLICY["schema_version"],1)
        self.assertEqual(POLICY["deployment_status"],"design_only_not_running")
        c=POLICY["control_plane"]
        self.assertFalse(c["cloud_scheduler_enabled"])
        self.assertFalse(c["duplicate_scheduler_allowed"])
        self.assertTrue(c["mac_native_requires_online_awake_session"])
        self.assertEqual(c["mac_executor"],"existing_user_launchagent_and_sqlite")
        self.assertEqual(c["state"],"cloudflare_d1")

    def test_preserve_named_employees_no_duplicate(self):
        self.assertEqual(POLICY["supervisor"]["employee"],"Walter")
        names=[item["name"] for item in POLICY["employees"]]
        self.assertEqual(set(names),{"Mike","Jane","Jesse","Gale","Gus","Saul","Hank"})
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual({r["id"] for r in ROLE["roles"]},{n.lower() for n in names})

    def test_preferred_routes_are_known_and_disabled(self):
        providers=POLICY["provider_capabilities"]
        self.assertEqual(set(providers),{"gemini","groq","nvidia_nim","mistral",
                                         "openrouter","cloudflare_workers_ai"})
        for p in providers.values():
            self.assertIs(p["configured"],False)
            self.assertIs(p["free_entitlement_verified"],False)
        self.assertEqual(POLICY["supervisor"]["recommended_planner"],"gemini")
        self.assertEqual(POLICY["work_type_preferences"]["goal_decomposition"],["gemini"])
        for opts in POLICY["work_type_preferences"].values():
            self.assertTrue(opts)
            self.assertTrue(set(opts) <= set(providers))

    def test_fail_closed_cost_and_retries(self):
        s=POLICY["safety"]
        self.assertFalse(s["default_paid_use_allowed"])
        self.assertTrue(s["unverified_model_is_ineligible"])
        self.assertEqual(s["fallback_provider"],"openrouter")
        self.assertEqual(s["dynamic_fallback"],"explicitly_verified_zero_cost_route_only")
        self.assertIs(s["side_effects_never_automatically_retried"],True)
        self.assertIs(s["legacy_failed_receipts_never_requeued"],True)
        self.assertEqual(s["transient_idempotent_retry_max_attempts"],3)
        self.assertEqual(s["existing_omniroute_rolling_24h_claim_cap"],5)
        self.assertTrue(s["stop_honored_on_every_dispatch"])
        self.assertFalse(s["client_or_secret_data_to_free_tiers_allowed"])

    def test_observability_and_canonical_doc_crosslinks(self):
        fields=set(POLICY["observability"]["durable_fields"])
        for item in ["job_id","role","dedupe_key","provider","exact_model_id",
                     "billing_eligibility_verified","attempts","receipt_ref"]:
            self.assertIn(item,fields)
        for name in ["Walter","Mike","Jane","Jesse","Gale","Gus","Saul","Hank"]:
            self.assertIn(name,ARCH)
        for p in ["Gemini","Groq","NVIDIA NIM","Mistral","OpenRouter","Cloudflare"]:
            self.assertIn(p,ARCH)
        for path in ["WORK.md","AGENTS.md","ROVOR-AI-PLAN.md"]:
            self.assertIn("HYBRID-24-7-GHOST-WORKFORCE.md",(ROOT/path).read_text())


if __name__=="__main__":
    unittest.main()
