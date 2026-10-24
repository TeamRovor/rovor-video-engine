"""Provider metadata audit never prints any supplied raw credential or ID."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import omniroute_provider_audit as probe

class ProbeTests(unittest.TestCase):
    def test_counts_named_connections_but_never_leaks_secret_fields(self):
        class Reply:
            returncode=0
            stdout='Header before JSON\n'+json.dumps({"providers":[
                {"provider":"groq","name":"private name","apiKey":"SECRET_123"},
                {"providerId":"openrouter","access_token":"ANOTHER_SECRET"},
                {"provider":"unknown-untrusted-account","id":"PRIVATE_EMAIL"}]})
        got=probe.audit(run=lambda *args,**kwargs:Reply())
        self.assertEqual(got["configured_connections_count"],3)
        self.assertEqual(got["provider_connection_counts"],
                         {"groq":1,"openrouter":1,"other":1})
        self.assertNotIn("SECRET",json.dumps(got))
        self.assertNotIn("PRIVATE_EMAIL",json.dumps(got))
        self.assertFalse(got["billing_eligibility_verified"])
        self.assertEqual(got["model_requests"],0)
    def test_unexpected_nonsecret_json_shape_is_classified_without_dumping(self):
        class Reply:
            returncode = 0
            stdout = '{"unexpected": {"secret": "PRIVATE_VALUE"}}'
        got = probe.audit(run=lambda *args, **kwargs: Reply())
        self.assertEqual(got["omniroute_cli_inventory"], "unavailable")
        self.assertEqual(got["sanitized_blocker"], "cli_json_shape_unrecognized")
        self.assertNotIn("PRIVATE_VALUE", json.dumps(got))

    def test_bad_cli_is_only_sanitized_unavailable(self):
        class Reply:
            returncode=2
            stdout='PRIVATE_ERROR'
        got=probe.audit(run=lambda *args,**kwargs:Reply())
        self.assertEqual(got["omniroute_cli_inventory"],"unavailable")
        self.assertNotIn("PRIVATE_ERROR",json.dumps(got))

if __name__=="__main__":
    unittest.main()
