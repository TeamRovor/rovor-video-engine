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

    def test_colored_cli_header_and_trailing_notice_parse_without_leaking(self):
        class Reply:
            returncode = 0
            stdout = (
                "\\x1b[36mOmniRoute providers\\x1b[0m\\n"
                + '{"providers":['
                + '{"provider":"openrouter","access_token":"DO_NOT_PRINT"},'
                + '{"providerId":"groq","apiKey":"SECRET_MUST_NOT_PRINT"}'
                + ']}\\nReady [local context]')
        result = probe.audit(run=lambda *args, **kwargs: Reply())
        self.assertEqual(result["omniroute_cli_inventory"],"parsed_safely")
        self.assertEqual(result["configured_connections_count"],2)
        self.assertEqual(result["provider_connection_counts"],
                         {"openrouter":1,"groq":1})
        self.assertNotIn("DO_NOT_PRINT",json.dumps(result))
        self.assertNotIn("SECRET_MUST_NOT_PRINT",json.dumps(result))

    def test_nested_list_envelope_parses_without_billing_claim(self):
        class Reply:
            returncode = 0
            stdout = 'CLI initialized\\n' + json.dumps({
                "data":{"connections":[{"provider":"mistral","apiKey":"PRIVATE"}]}})
        result = probe.audit(run=lambda *args, **kwargs: Reply())
        self.assertEqual(result["configured_connections_count"],1)
        self.assertEqual(result["provider_connection_counts"],{"mistral":1})
        self.assertFalse(result["billing_eligibility_verified"])

    def test_bad_cli_is_only_sanitized_unavailable(self):
        class Reply:
            returncode=2
            stdout='PRIVATE_ERROR'
        got=probe.audit(run=lambda *args,**kwargs:Reply())
        self.assertEqual(got["omniroute_cli_inventory"],"unavailable")
        self.assertNotIn("PRIVATE_ERROR",json.dumps(got))

if __name__=="__main__":
    unittest.main()
