"""Regression tests for portable work packet v1; stdlib only."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "architecture" / "contracts" / "work-packet"
sys.path.insert(0, str(CONTRACT))
from validate import evaluate, validate_packet, read_json


class WorkPacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = read_json(CONTRACT / "examples.json")
        cls.invalid = read_json(CONTRACT / "invalid-examples.json")

    def test_three_evaluation_families_are_represented(self):
        self.assertEqual({p["capability"] for p in self.valid["packets"]},
                         {"client_intake", "sourced_sales", "ci_triage"})
        self.assertEqual(len(self.valid["packets"]), 3)

    def test_reference_packets_pass(self):
        self.assertEqual(evaluate(self.valid)["summary"],
                         {"passed": 3, "failed": 0, "total": 3})

    def test_deliberately_invalid_packets_fail(self):
        self.assertEqual(evaluate(self.invalid)["summary"],
                         {"passed": 0, "failed": 3, "total": 3})

    def test_fixtures_reference_evaluation_cases(self):
        refs = [s["uri"] for p in self.valid["packets"] for s in p["source_refs"]]
        self.assertTrue(any(
            "blob/3a5520da17bb1373193bb552673f8abdeba484b9/architecture/evaluations/cases.json" in uri
            for uri in refs
        ))
        self.assertTrue(any("39683961823" in uri for uri in refs))

    def test_unknown_and_unrun_states_are_preserved(self):
        for packet in self.valid["packets"]:
            self.assertEqual(packet["technical_status"], "not_run")
            self.assertEqual(packet["acceptance"][0]["status"], "not_run")
            self.assertEqual(packet["artifact_receipt"]["state"], "not_created")
            self.assertEqual(packet["approval"]["state"], "draft")

    def test_technical_pass_requires_all_acceptance_evidence(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["technical_status"] = "passed"
        self.assertIn("pass_without_acceptance",
                      {x["code"] for x in validate_packet(packet)})

    def test_technical_pass_can_remain_unapproved(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["technical_status"] = "passed"
        packet["acceptance"][0]["status"] = "pass"
        packet["acceptance"][0]["evidence_refs"] = ["demo-intake-v1"]
        self.assertEqual(validate_packet(packet), [])
        self.assertEqual(packet["approval"]["state"], "draft")

    def test_verified_source_requires_hash(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["source_refs"][0]["status"] = "verified"
        self.assertIn("verified_source_without_hash",
                      {x["code"] for x in validate_packet(packet)})

    def test_unknown_evidence_reference_is_rejected(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["acceptance"][0]["evidence_refs"] = ["missing-source"]
        self.assertIn("unknown_evidence_ref",
                      {x["code"] for x in validate_packet(packet)})

    def test_external_effect_cannot_be_self_granted(self):
        packet = copy.deepcopy(self.valid["packets"][1])
        packet["authorization"] = {
            "state": "granted", "effects": ["contact_external"], "source_refs": []
        }
        codes = {x["code"] for x in validate_packet(packet)}
        self.assertIn("unauthorized_effect", codes)
        self.assertIn("grant_without_evidence", codes)

    def test_publishing_needs_explicit_source_reference(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["approval"] = {"state": "published", "source_refs": []}
        self.assertIn("approval_without_evidence",
                      {x["code"] for x in validate_packet(packet)})

    def test_verified_artifact_requires_hash(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["artifact_receipt"] = {"state": "verified", "artifacts": [
            {"id": "render-1", "uri": "artifact://render-1",
             "status": "verified", "sha256": None}
        ]}
        codes = {x["code"] for x in validate_packet(packet)}
        self.assertIn("verified_artifact_without_hash", codes)
        self.assertIn("receipt_without_verified_artifact", codes)

    def test_opaque_payload_field_is_rejected(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["shell"] = "opaque payload"
        self.assertIn("forbidden_payload",
                      {x["code"] for x in validate_packet(packet)})

    def test_duplicate_packet_ids_are_rejected(self):
        batch = copy.deepcopy(self.valid)
        batch["packets"].append(copy.deepcopy(batch["packets"][0]))
        self.assertIn("duplicate_packet_id",
                      {x["code"] for result in evaluate(batch)["results"]
                       for x in result["issues"]})

    def test_non_object_packet_returns_structured_failure(self):
        result = evaluate({"version": 1, "packets": ["not an object"]})
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertIn("invalid_packet",
                      {x["code"] for x in result["results"][0]["issues"]})

    def test_malformed_enum_values_and_packet_id_do_not_crash(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["constraints"]["data_classification"] = []
        packet["artifact_receipt"]["state"] = []
        packet["approval"]["state"] = []
        self.assertTrue(validate_packet(packet))
        batch = {"version": 1, "packets": [{"packet_id": []}]}
        self.assertEqual(evaluate(batch)["summary"]["failed"], 1)

    def test_boolean_schema_version_is_not_integer_one(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["schema_version"] = True
        self.assertIn("schema_version",
                      {x["code"] for x in validate_packet(packet)})

    def test_validator_enforces_schema_collection_and_uri_limits(self):
        packet = copy.deepcopy(self.valid["packets"][0])
        packet["source_refs"] = packet["source_refs"] * 51
        packet["artifact_receipt"] = {"state": "produced", "artifacts": [
            {"id": "artifact-1", "uri": "x" * 2049,
             "status": "unverified", "sha256": None}
        ] * 51}
        packet["acceptance"] = packet["acceptance"] * 51
        codes = {x["code"] for x in validate_packet(packet)}
        self.assertIn("source_limit", codes)
        self.assertIn("artifact_limit", codes)
        self.assertIn("artifact_uri", codes)
        self.assertIn("acceptance_limit", codes)

    def test_input_size_guard(self):
        path = CONTRACT / "oversize-fixture.tmp"
        try:
            path.write_bytes(b" " * 200_001)
            with self.assertRaisesRegex(ValueError, "oversized"):
                read_json(path)
        finally:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
