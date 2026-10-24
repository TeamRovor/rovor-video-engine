import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_model_fleet as fleet

def model(n):
    return {"kind": "model", "providerId": "openrouter",
            "model": "openrouter/vendor/model-%d:free" % n}

class ModelFleetTests(unittest.TestCase):
    def setUp(self):
        self.providers = {"connections": [
            {"providerId": "openrouter", "secret": "DO_NOT_LOG_THIS"},
            {"providerId": "groq"}]}
        self.combos = {"combos": [
            {"name": "rovor-fast-free-v1", "strategy": "priority",
             "models": [model(1), model(2)]},
            {"name": "rovor-reason-free-v1", "strategy": "priority",
             "models": [model(2), model(3)]}]}

    def test_configured_connections_not_confused_with_models(self):
        result = fleet.inspect(self.providers, self.combos)
        self.assertEqual(result["connection_entries"], 2)
        self.assertEqual(result["distinct_routed_models"], 3)
        self.assertEqual(result["models_not_visible_in_rovor_routes"], 6)
        self.assertEqual(result["model_requests"], 0)
        self.assertFalse(result["working_models_verified"])
        self.assertNotIn("DO_NOT_LOG_THIS", json.dumps(result))
        self.assertEqual(len(result["worker_route_coverage"]), 8)

    def test_nine_routed_models_not_automatic_success(self):
        self.combos["combos"][0]["models"] = [model(n) for n in range(1, 10)]
        result = fleet.inspect(self.providers, self.combos)
        self.assertEqual(result["distinct_routed_models"], 9)
        self.assertEqual(result["models_not_visible_in_rovor_routes"], 0)
        self.assertFalse(result["upstream_free_quota_verified"])
        self.assertFalse(result["unattended_job_completion_verified"])

    def test_packet_mapping_and_mismatch(self):
        routes = {"Jesse": ("rovor-fast-free-v1", [model(2)["model"], model(1)["model"]]),
                  "Jane": ("rovor-missing", [model(1)["model"]]),
                  "Hank": ("rovor-fast-free-v1", [model(1)["model"], model(2)["model"]])}
        rows = fleet.inspect(self.providers, self.combos, routes=routes)["worker_route_coverage"]
        self.assertEqual(rows["Jesse"]["status"], "members_changed")
        self.assertEqual(rows["Jane"]["status"], "route_missing")
        self.assertEqual(rows["Hank"]["status"], "configured_not_inference_verified")
        self.assertEqual(rows["Walter"]["status"], "source_not_available")

    def test_nonfree_fallback_is_visible_not_approved(self):
        self.combos["combos"][0]["models"].append(
            {"kind": "model", "providerId": "mistral", "model": "mistral/paid"})
        data = fleet.inspect(self.providers, self.combos)
        self.assertFalse(data["combos"]["rovor-fast-free-v1"]["free_suffix_only"])
        self.assertFalse(data["upstream_free_quota_verified"])

    def test_duplicate_rovor_route_rejected(self):
        self.combos["combos"].append(self.combos["combos"][0])
        with self.assertRaises(fleet.FleetError):
            fleet.inspect(self.providers, self.combos)

    def test_duplicate_member_rejected(self):
        self.combos["combos"][0]["models"] = [model(1), model(1)]
        with self.assertRaises(fleet.FleetError):
            fleet.inspect(self.providers, self.combos)

    def test_reject_unstructured_or_secret_kind_model(self):
        self.combos["combos"][0]["models"][0]["kind"] = "credential"
        with self.assertRaises(fleet.FleetError):
            fleet.inspect(self.providers, self.combos)
        with self.assertRaises(fleet.FleetError):
            fleet.inspect({"connections": [{}] * 201}, self.combos)

    def test_banner_without_leaking_raw_error(self):
        result = SimpleNamespace(returncode=0,
            stdout=b"OmniRoute ready\n" + json.dumps(self.combos).encode("utf-8"),
            stderr=b"SECRET_FROM_GATEWAY")
        self.assertEqual(fleet.read_cli(["omniroute", "combo", "list", "--json"],
                         run=lambda *a, **k: result), self.combos)

    def test_failure_never_returns_cli_secrets(self):
        bad = SimpleNamespace(returncode=1, stdout=b"TOKEN_SHOULD_NOT_PRINT",
                              stderr=b"PRIVATE_KEY")
        with self.assertRaisesRegex(fleet.FleetError, "^cli_failed_or_oversized$"):
            fleet.read_cli(["omniroute"], run=lambda *a, **k: bad)

    def test_eight_employee_packet_identities_preserved(self):
        self.assertEqual(set(fleet.PACKETS),
            {"Walter", "Mike", "Jane", "Jesse", "Gale", "Gus", "Saul", "Hank"})

if __name__ == "__main__":
    unittest.main()
