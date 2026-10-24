"""Readiness checks never run models, expose secrets or mutate runtime."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import omniroute_readiness_audit as app
import ghost_omniroute_job as omni


class Result:
    def __init__(self, code=0, data=""):
        self.returncode = code
        self.stdout = data


def catalog():
    # Fixed mock route schema, no provider invocation or account keys.
    return [{"name":name,"strategy":"priority","isHidden":False,
             "models":[{"kind":"model","providerId":"openrouter","model":m}
                       for m in models]}
            for name,models in dict.fromkeys(omni.ROUTES.values())]


class ReadinessTests(unittest.TestCase):
    def test_read_only_sanitized_inventory_and_authenticated_get(self):
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            if argv[1:3] == ["providers","list"]:
                return Result(data='Banner\\n' + json.dumps({"providers":[
                    {"providerId":"groq","apiKey":"SECRET_NEVER_LOG"},
                    {"provider":"gemini","name":"PRIVATE_ACCOUNT"},
                ]}))
            if argv[1:3] == ["providers","validate"]:
                return Result(data="PROVIDER_SECRET_IN_STDOUT")
            raise AssertionError("Unexpected external process")
        def gateway_open(req, timeout):
            self.assertEqual(req.get_method(),"GET")
            self.assertEqual(req.full_url,"http://127.0.0.1:20128/v1/models")
            self.assertEqual(req.get_header("Authorization"),"Bearer private-key")
            class Response:
                status=200
                def __enter__(self): return self
                def __exit__(self,*args): return False
            return Response()
        result = app.audit(
            run=run,read_catalog=catalog,
            key_getter=lambda:"private-key",gateway_open=gateway_open,
            read_worker=lambda state:{
                "launchagent_loaded":True,"stop_requested":False,
                "database_status":"snapshot_readable",
                "ai_claims_last_24h":10,
                "inference_claim_guard_would_block":True,
                "omniroute_draft_counts":{"review_ready":1},
                "private_text":"PRIVATE_DRAFT"})
        self.assertEqual(result["configured_connections_count"],2)
        self.assertEqual(result["loopback_models_get"],"authenticated_http_200")
        self.assertEqual(result["combo_catalog_status"],"readable")
        self.assertTrue(all(x=="configured_expected_free_suffix"
                            for x in result["approved_combo_configs"].values()))
        self.assertEqual(result["model_requests"],0)
        self.assertEqual(result["upstream_provider_tests"],0)
        self.assertFalse(result["route_free_of_charge_verified"])
        self.assertFalse(result["provider_connections_working_verified"])
        self.assertEqual(result["existing_worker"]["review_ready_drafts"],1)
        self.assertEqual(len(calls),2)
        for private in ("SECRET_NEVER_LOG","PROVIDER_SECRET_IN_STDOUT",
                        "PRIVATE_ACCOUNT","private-key","PRIVATE_DRAFT"):
            self.assertNotIn(private,json.dumps(result))

    def test_bad_local_cli_does_not_become_provider_health_confirmation(self):
        result = app.audit(
            run=lambda argv,**kwargs:Result(2,"PRIVATE_ERROR"),
            read_catalog=lambda: (_ for _ in ()).throw(ValueError("SECRET")),
            key_getter=lambda: (_ for _ in ()).throw(ValueError("SECRET")),
            gateway_open=lambda *args,**kwargs: self.fail("not called"),
            read_worker=lambda state:{"database_status":"missing"})
        self.assertEqual(result["provider_configuration_cli"],"nonzero_exit")
        self.assertEqual(result["combo_catalog_status"],"unavailable")
        self.assertEqual(result["loopback_models_get"],"unavailable_or_refused")
        self.assertEqual(result["model_requests"],0)
        self.assertNotIn("SECRET",json.dumps(result))


if __name__=="__main__":
    unittest.main()
