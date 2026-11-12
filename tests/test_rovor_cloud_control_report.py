"""Offline tests for the non-mutating Mac-independent ROVOR control report."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import rovor_cloud_control_report as ops


class Reply:
    status = 200
    def __init__(self, obj): self.data = json.dumps(obj).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self, n): return self.data[:n]


class HTTP:
    def __init__(self, token): self.token = token; self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        url = request.full_url
        if url == ops.HUD_ORIGIN + "/api/hud/status" and request.get_header("Authorization") is None:
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
        if url == ops.HUD_ORIGIN + "/api/hud/status?period=24h":
            return Reply({"source":"cloud_hud_telemetry","connection":"stale","snapshot":{
                "connections":[{"provider":p} for p in sorted(ops.PROVIDERS)]}})
        if url == ops.HUD_ORIGIN + "/api/hud/gemini/models":
            return Reply({"source":"google_gemini_cloud_direct","online":True,
                          "models":["gemini-auto-free","gemini-3.1-flash-lite"],"mac_required":False})
        if url == ops.HUD_ORIGIN + "/api/hud/gemini/usage":
            return Reply({"source":"cloud_gemini_direct","completed":2,"models":[{"model":"gemini-3.1-flash-lite","completed":2}]})
        if url == ops.HUD_ORIGIN + "/api/chat/models":
            return Reply({"models":["@cf/google/gemma-3-12b-it"]})
        if url == ops.HUD_ORIGIN + "/api/hud/chat/models":
            return Reply({"online":False,"models":[]})
        if url == ops.SITE_ORIGIN + "/api/ghost/service":
            assert request.get_method() == "POST"
            assert request.data == b'{"operation":"status"}'
            assert request.get_header("Authorization") == "Bearer " + self.token
            return Reply({"execution_source":"cloud_provider", "enabled":True,
                          "providers":[{"provider":p,"credentials_configured":True,
                                        "online_verified":False,
                                        "admission":"disabled_pending_verification"} for p in sorted(ops.PROVIDERS)],
                          "queue_pending":0,"review_queue":{"pending_count":3},
                          "employees":[{"name":name} for name in
                            ("Walter","Mike","Jane","Jesse","Gale","Gus","Saul","Hank")],
                          "scheduled_shifts":{"runs":[{"status":"idle"}]},
                          "native_clock_verified":False, "attempts":[{"status":"needs_review"}]})
        raise AssertionError("unexpected URL: " + url)


def env():
    return {
        "ROVOR_CONTROL_MODE":"deploy_and_test_gemini",
        "ROVOR_OWNER_CONFIRMS_FREE_TIER":"true",
        "CLOUDFLARE_API_TOKEN":"private-api-token",
        "CLOUDFLARE_ACCOUNT_ID":"a"*32,
        "ROVOR_HUD_D1_ID":"11111111-1111-1111-1111-111111111111",
        "ROVOR_HUD_WRITER_TOKEN":"w"*48,
        "ROVOR_HUD_READER_TOKEN":"r"*48,
        "ROVOR_HUD_DEPLOY_ORIGIN":ops.HUD_ORIGIN,
        "ROVOR_GEMINI_API_KEY":"g"*38,
        "ROVOR_GHOST_SERVICE_TOKEN":"s"*48,
    }


class ControlReportTests(unittest.TestCase):
    def test_no_mac_dependency_two_cloud_services_and_no_secrets(self):
        e=env();client=HTTP(e["ROVOR_GHOST_SERVICE_TOKEN"])
        report=ops.build_report(e, opener=client)
        self.assertTrue(report["deploy_ready"])
        self.assertFalse(report["mac_required"])
        self.assertEqual(report["hud"]["private"],"verified_401")
        self.assertEqual(report["hud"]["gemini_cloud"],"key_listed_free_text_models")
        self.assertEqual(report["hud"]["gemini_free_text_models_listed"],1)
        self.assertEqual(report["hud"]["gemini_models_with_replies_today"],1)
        self.assertEqual(report["hud"]["gemini_completed_today"],2)
        self.assertEqual(report["hud"]["mac_telemetry_optional"],"stale")
        self.assertTrue(report["workforce"]["nine_provider_records"])
        self.assertEqual(report["workforce"]["configured_provider_count"],9)
        self.assertEqual(report["workforce"]["verified_online_providers"],0)
        self.assertEqual(report["workforce"]["eligible_providers"],0)
        self.assertEqual(len(report["workforce"]["provider_readiness"]),9)
        self.assertTrue(all(row["online"] == "not_verified"
                            for row in report["workforce"]["provider_readiness"]))
        self.assertEqual(report["workforce"]["pending_reviews"],3)
        self.assertEqual(report["workforce"]["reported_employee_roles"],8)
        self.assertEqual(report["workforce"]["last_scheduled_shift"],"idle")
        for secret in (e["ROVOR_GEMINI_API_KEY"],e["ROVOR_HUD_READER_TOKEN"],
                       e["ROVOR_HUD_WRITER_TOKEN"],e["ROVOR_GHOST_SERVICE_TOKEN"]):
            self.assertNotIn(secret,json.dumps(report))
            self.assertNotIn(secret,ops.summary(report))
        for request in client.requests:
            self.assertEqual(request.get_method(),"POST" if request.full_url.endswith("/api/ghost/service") else "GET")

    def test_missing_gemini_key_does_not_block_audit_but_blocks_canary_mode(self):
        e=env();e["ROVOR_GEMINI_API_KEY"]=""
        self.assertFalse(ops.can_deploy(ops.deployment_secrets(e),"deploy_and_test_gemini",True))
        self.assertTrue(ops.can_deploy(ops.deployment_secrets(e),"deploy_existing_hud",False))
        e["ROVOR_CONTROL_MODE"]="audit_only"
        report=ops.build_report(e,opener=HTTP(e["ROVOR_GHOST_SERVICE_TOKEN"]))
        self.assertEqual(report["mode"],"audit_only")
        self.assertFalse(report["credentials_present"]["google_free_project_key"])
        self.assertNotIn("google_free_project_key",report["missing_deployment_prerequisites"])

    def test_preexisting_cloudflare_gemini_secret_can_be_reused_without_github_key(self):
        e=env()
        e["ROVOR_GEMINI_API_KEY"]=""
        e["ROVOR_CLOUDFLARE_GEMINI_SECRET_PRESENT"]="true"
        self.assertTrue(ops.deployment_secrets(e)["google_free_project_key"])
        self.assertTrue(ops.can_deploy(ops.deployment_secrets(e),"deploy_and_test_gemini",True))
        self.assertFalse(ops.can_deploy(ops.deployment_secrets(e),"deploy_and_test_gemini",False))

    def test_nine_provider_readiness_is_redacted_and_keeps_catalog_separate(self):
        now = 1794455910000
        rows = [
            {"provider": provider, "credentials_configured": True,
             "configured_model": None, "admission": "disabled_pending_verification",
             "online_verified": False, "last_check": None}
            for provider in sorted(ops.PROVIDERS)
        ]
        groq = next(row for row in rows if row["provider"] == "groq")
        groq.update({
            "configured_model": "openai/gpt-oss-20b",
            "admission": "eligibility_expired",
            "online_verified": True,
            "last_check": {"provider": "groq", "observed_at": now,
                           "status": "catalog_received"},
        })
        result = ops.provider_readiness(rows, now_ms=now)
        self.assertEqual(len(result), 9)
        observed = next(row for row in result if row["provider"] == "groq")
        self.assertEqual(observed["credentials"], "configured")
        self.assertEqual(observed["catalog"], "fresh_authenticated")
        self.assertEqual(observed["model"], "declared_pinned")
        self.assertEqual(observed["admission"], "eligibility_expired")
        self.assertEqual(observed["online"], "not_verified")
        self.assertNotIn("gpt-oss-20b", json.dumps(result),
                         "the readiness audit must not log raw operator model config")

        untrusted = next(row for row in rows if row["provider"] == "nvidia")
        untrusted["admission"] = "bad | markdown\\nAuthorization: Bearer PRIVATE"
        untrusted["configured_model"] = "auto"
        untrusted["last_check"] = {"provider": "nvidia",
                                   "status": "catalog_received",
                                   "observed_at": now - ops.CATALOG_FRESH_MS - 1}
        sanitized = ops.provider_readiness(rows, now_ms=now)
        entry = next(row for row in sanitized if row["provider"] == "nvidia")
        self.assertEqual(entry["admission"], "unclassified")
        self.assertEqual(entry["catalog"], "stale")
        self.assertEqual(entry["model"], "not_pinned")
        self.assertNotIn("Bearer PRIVATE", json.dumps(sanitized))

        # Markdown sanitization is tested using the real report shape below.
        report = ops.build_report(env(), opener=HTTP(env()["ROVOR_GHOST_SERVICE_TOKEN"]))
        report["workforce"]["provider_readiness"] = sanitized
        rendered = ops.summary(report)
        self.assertIn("Nine-provider admission detail", rendered)
        self.assertIn("eligibility_expired", rendered)
        self.assertNotIn("Bearer PRIVATE", rendered)
        self.assertNotIn("gpt-oss-20b", rendered)

    def test_malformed_provider_readiness_fails_closed_without_runtime_errors(self):
        valid = [{"provider": p, "admission": {"untrusted": "raw"}}
                 for p in sorted(ops.PROVIDERS)]
        result = ops.provider_readiness(valid, now_ms=1794455910000)
        self.assertEqual(len(result), 9)
        self.assertTrue(all(row["admission"] == "unclassified" for row in result))
        self.assertEqual(ops.provider_readiness(valid[:-1]), [])
        valid[0]["provider"] = ["not", "hashable"]
        self.assertEqual(ops.provider_readiness(valid), [])

    def test_site_service_key_missing_is_truthfully_unverified(self):
        e=env();e.pop("ROVOR_GHOST_SERVICE_TOKEN")
        report=ops.build_report(e,opener=HTTP("s"*48))
        self.assertEqual(report["workforce"]["service"],"blocked_service_secret_missing")
        self.assertIsNone(report["workforce"]["eligible_providers"])

    def test_reject_wrong_origin_unknown_status_or_shift_request(self):
        with self.assertRaisesRegex(ValueError,"unapproved_status_target"):
            ops.safe_request("https://evil.example","/api/hud/status")
        with self.assertRaisesRegex(ValueError,"unapproved_status_body"):
            ops.safe_request(ops.SITE_ORIGIN,ops.GHOST_ROUTE,"s"*48,
                             method="POST",document={"operation":"shift"})
        with self.assertRaisesRegex(ValueError,"unapproved_status_operation"):
            ops.safe_request(ops.HUD_ORIGIN,"/api/hud/status",method="POST")

    def test_header_format_and_stop_are_not_ignored(self):
        self.assertFalse(ops.credential("abc\n123"))
        self.assertFalse(ops.credential("a"*16))
        self.assertTrue(ops.credential("a"*48))
        e=env();e["ROVOR_HUD_WRITER_TOKEN"]=e["ROVOR_HUD_READER_TOKEN"]
        self.assertFalse(ops.deployment_secrets(e)["private_hud_writer"])


    def test_legacy_control_center_cannot_replace_production_worker(self):
        source = (ROOT / ".github/workflows/rovor-cloud-control-center.yml").read_text()
        protected = (ROOT / ".github/workflows/deploy-private-hud-cloudflare.yml").read_text()
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("audit_only", source)
        self.assertNotIn("deploy_existing_hud", source)
        self.assertNotIn("deploy_and_test_gemini", source)
        self.assertNotIn("  deploy-hud:", source)
        self.assertNotIn("  gemini-canary:", source)
        self.assertNotIn("wrangler deploy", source)
        self.assertNotIn("wrangler secret bulk", source)
        self.assertNotIn("wrangler d1 execute DB --remote", source)
        self.assertNotIn("  schedule:", source)
        self.assertIn("inputs.verify_provider_catalog_readback == true", source)
        self.assertNotIn("github.event_name == 'push' ||", source)
        self.assertIn("deploy-private-hud-cloudflare.yml", source)
        self.assertIn("workflow_dispatch:", protected)
        self.assertIn("branches: [main]", protected)
        self.assertIn("wrangler deploy --config wrangler.github.jsonc", protected)
        self.assertIn("wrangler secret bulk --config wrangler.github.jsonc", protected)
        self.assertIn("Verify independent GitHub", protected)



if __name__=="__main__":
    unittest.main()
