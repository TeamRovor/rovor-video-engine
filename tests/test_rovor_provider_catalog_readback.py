"""No-secret tests for catalog readback of the existing owner-private ROVOR Site."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import verify_rovor_provider_catalog_readback as check
from tools import rovor_cloud_control_report as control

TOKEN = "s" * 48


class FakeSite:
    def __init__(self, stale=None, malformed=None):
        self.stale = stale
        self.malformed = malformed
        self.rows = {}
        self.calls = []

    def __call__(self, origin, route, token, method, document):
        assert origin == control.SITE_ORIGIN
        assert route == control.GHOST_ROUTE
        assert token == TOKEN
        assert method == "POST"
        self.calls.append(document)
        if document["operation"] == "inventory":
            provider = document["provider"]
            assert provider in control.PROVIDERS
            if provider == self.malformed:
                return 200, {"provider": "wrong-provider", "status": "catalog_received"}, None
            observed_at = 1794294800000 + list(check.PROVIDERS).index(provider)
            self.rows[provider] = {
                "provider": provider, "observed_at": observed_at - (1 if provider == self.stale else 0),
                "status": "catalog_received", "error_category": None
            }
            return 200, {
                "provider": provider, "status": "catalog_received",
                "observed_at": observed_at, "models": [{"id": "redacted-model"}],
                "billing_verified": False, "quota_verified": False, "canary_verified": False,
            }, None
        assert document == {"operation": "status"}
        return 200, {
            "execution_source": "cloud_provider",
            "providers": [
                {"provider": p, "last_check": self.rows.get(p),
                 "admission": "disabled_pending_verification"}
                for p in check.PROVIDERS
            ],
        }, None


class CatalogReadbackTests(unittest.TestCase):
    def test_nine_catalogs_must_match_exact_private_d1_timestamps(self):
        client = FakeSite()
        report = check.audit_catalog_persistence(TOKEN, request=client)
        self.assertEqual(report["state"], "catalog_persistence_verified")
        self.assertEqual(report["catalog_received"], 9)
        self.assertEqual(report["persisted"], 9)
        self.assertFalse(report["inference_verified"])
        self.assertFalse(report["free_billing_verified"])
        self.assertEqual(len(client.calls), 11)
        self.assertEqual(client.calls[0], {"operation": "status"})
        self.assertEqual(client.calls[-1], {"operation": "status"})
        self.assertTrue(all(c["operation"] == "inventory" for c in client.calls[1:-1]))

    def test_stale_site_timestamp_fails_even_with_successful_live_catalogs(self):
        report = check.audit_catalog_persistence(
            TOKEN, request=FakeSite(stale="gemini")
        )
        self.assertEqual(report["catalog_received"], 9)
        self.assertEqual(report["persisted"], 8)
        self.assertEqual(report["state"], "catalog_or_persistence_incomplete")
        self.assertFalse(next(r for r in report["providers"] if r["provider"] == "gemini")["persisted"])
        self.assertIn("not confirmed", check.markdown(report))

    def test_mismatched_provider_is_not_accepted_as_success(self):
        report = check.audit_catalog_persistence(
            TOKEN, request=FakeSite(malformed="groq")
        )
        self.assertEqual(report["catalog_received"], 8)
        self.assertEqual(report["persisted"], 8)
        self.assertEqual(report["state"], "catalog_or_persistence_incomplete")

    def test_missing_secret_makes_zero_requests(self):
        client = FakeSite()
        report = check.audit_catalog_persistence("short", request=client)
        self.assertEqual(report["state"], "service_secret_missing")
        self.assertEqual(client.calls, [])
        self.assertEqual(report["providers"], [])


    def test_private_site_auth_failure_is_not_reported_as_nine_provider_failures(self):
        for code, state in [
            (401, "site_service_auth_denied"),
            (403, "site_service_auth_denied"),
            (302, "site_service_login_redirect"),
            (503, "site_service_http_unavailable"),
            (0, "site_service_transport_unavailable"),
        ]:
            calls = []

            def denied(origin, route, token, method, document):
                calls.append(document)
                return code, None, "untrusted vendor body must not appear"

            report = check.audit_catalog_persistence(TOKEN, request=denied)
            self.assertEqual(report["state"], state)
            self.assertEqual(report["site_http_code"], code)
            self.assertEqual(report["catalog_received"], 0)
            self.assertEqual(report["persisted"], 0)
            self.assertEqual(calls, [{"operation": "status"}])
            self.assertNotIn("untrusted vendor body", check.markdown(report))
            self.assertIn(state, check.markdown(report))

    def test_private_site_invalid_status_schema_sends_no_provider_catalog_calls(self):
        calls = []
        def malformed(origin, route, token, method, document):
            calls.append(document)
            return 200, {"execution_source": "cloud_provider", "providers": []}, None
        report = check.audit_catalog_persistence(TOKEN, request=malformed)
        self.assertEqual(report["state"], "site_service_contract_invalid")
        self.assertEqual(report["site_http_code"], 200)
        self.assertEqual(calls, [{"operation": "status"}])

    def test_original_status_client_remains_strict_and_inventory_is_fixed(self):
        with self.assertRaisesRegex(ValueError, "unapproved_status_body"):
            control.safe_request(control.SITE_ORIGIN, control.GHOST_ROUTE, TOKEN,
                                 method="POST", document={"operation": "shift"})
        with self.assertRaisesRegex(ValueError, "unapproved_status_body"):
            control.safe_request(control.SITE_ORIGIN, control.GHOST_ROUTE, TOKEN,
                                 method="POST", document={"operation": "inventory",
                                                          "provider": "attacker"})
        with self.assertRaisesRegex(ValueError, "unapproved_status_body"):
            control.safe_request(control.SITE_ORIGIN, control.GHOST_ROUTE, TOKEN,
                                 method="POST", document={"operation": "inventory",
                                                          "provider": "groq", "prompt": "attack"})


if __name__ == "__main__":
    unittest.main()
