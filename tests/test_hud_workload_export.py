"""Offline workload exporter regression: counts, unknowns, privacy and failures."""
from datetime import datetime, timedelta, timezone
import json
import unittest

from tools import hud_workload_export as workload


NOW = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)
FLEET = {
    "kind": "omniroute_actual_model_coverage",
    "routed_model_ids": ["openrouter/model-a:free", "gemini/model-b"],
    "nine_model_target": 9,
    "connections": [{"credential": "DO_NOT_ECHO_KEY"}],
}
RECEIPTS = [
    {"receipt_id": "r_01", "employee": "jane",
     "model_id": "openrouter/model-a:free",
     "timestamp": "2026-10-24T08:55:00Z", "outcome": "completed",
     "prompt": "NEVER_ECHO_PRIVATE_PROMPT", "key": "DO_NOT_ECHO_KEY"},
    {"receipt_id": "r_02", "employee": "walter",
     "model_id": "gemini/model-b",
     "timestamp": "2026-10-24T07:00:00Z", "outcome": "failed"},
    {"receipt_id": "r_03", "employee": "jane",
     "model_id": "gemini/model-b",
     "timestamp": "2026-10-22T15:00:00Z", "outcome": "completed"},
]


class ExportTests(unittest.TestCase):
    def test_no_receipts_means_unknown_not_zero(self):
        out = workload.build_snapshot(FLEET, now=NOW)
        self.assertFalse(out["verified_live"])
        self.assertEqual(out["source"], "unattested_local_export")
        self.assertEqual(out["inventory"]["actual_models"], 2)
        self.assertEqual(out["inventory"]["missing_from_expected"], 7)
        self.assertEqual(out["usage"]["state"], "unknown")
        self.assertIsNone(out["usage"]["windows"]["24h"])
        self.assertIsNone(out["usage"]["quota_remaining"])
        self.assertIsNone(out["usage"]["cost_usd"])

    def test_settled_receipts_are_counted_by_model_role_period(self):
        out = workload.build_snapshot(FLEET, RECEIPTS, now=NOW)
        one = out["usage"]["windows"]["1h"]
        day = out["usage"]["windows"]["24h"]
        week = out["usage"]["windows"]["7d"]
        self.assertEqual((one["request_count"], day["request_count"],
                          week["request_count"]), (1, 2, 3))
        self.assertEqual(one["model_counts"]["openrouter/model-a:free"], 1)
        self.assertEqual(day["model_counts"]["gemini/model-b"], 1)
        self.assertEqual(day["employee_model_counts"]["jane"]["openrouter/model-a:free"], 1)
        self.assertEqual(day["employee_model_counts"]["walter"]["gemini/model-b"], 1)
        self.assertEqual((day["completed_count"], day["failed_count"]), (1, 1))
        self.assertEqual(out["usage"]["coverage"], "unknown")
        self.assertEqual(out["usage"]["state"], "unattested_receipt_counts")
        raw = json.dumps(out)
        self.assertNotIn("DO_NOT_ECHO_KEY", raw)
        self.assertNotIn("NEVER_ECHO_PRIVATE_PROMPT", raw)
        self.assertNotIn("receipt_id", raw)

    def test_empty_receipt_file_is_not_verified_live_zero(self):
        out = workload.build_snapshot(FLEET, [], now=NOW)
        self.assertEqual(out["usage"]["windows"]["1h"]["request_count"], 0)
        self.assertFalse(out["verified_live"])
        self.assertEqual(out["usage"]["coverage"], "unknown")

    def test_duplicate_receipt_refused(self):
        with self.assertRaisesRegex(workload.SnapshotError, "receipt_duplicate"):
            workload.build_snapshot(FLEET, [RECEIPTS[0], RECEIPTS[0]], now=NOW)

    def test_unknown_model_or_role_refused(self):
        event = {**RECEIPTS[0], "model_id": "some-other-model"}
        with self.assertRaisesRegex(workload.SnapshotError, "receipt_unknown_route"):
            workload.build_snapshot(FLEET, [event], now=NOW)
        event = {**RECEIPTS[0], "employee": "stranger"}
        with self.assertRaisesRegex(workload.SnapshotError, "receipt_unknown_route"):
            workload.build_snapshot(FLEET, [event], now=NOW)

    def test_inventory_rejects_duplicates(self):
        fleet = {**FLEET, "routed_model_ids": ["gemini/model-b"] * 2}
        with self.assertRaisesRegex(workload.SnapshotError, "fleet_model_duplicate"):
            workload.build_snapshot(fleet, now=NOW)

    def test_naive_and_future_timestamps_fail(self):
        event = {**RECEIPTS[0], "timestamp": "2026-10-24T08:00:00"}
        with self.assertRaisesRegex(workload.SnapshotError, "timestamp_must_be_utc"):
            workload.build_snapshot(FLEET, [event], now=NOW)
        event = {**RECEIPTS[0], "timestamp": "2026-10-24T10:00:00Z"}
        with self.assertRaisesRegex(workload.SnapshotError, "receipt_future_timestamp"):
            workload.build_snapshot(FLEET, [event], now=NOW)

    def test_rejects_unsettled_event_and_untrusted_fleet_shape(self):
        event = {**RECEIPTS[0], "outcome": "in_progress"}
        with self.assertRaisesRegex(workload.SnapshotError, "receipt_outcome_invalid"):
            workload.build_snapshot(FLEET, [event], now=NOW)
        with self.assertRaisesRegex(workload.SnapshotError, "fleet_report_invalid"):
            workload.build_snapshot({"models": ["x"]}, now=NOW)


if __name__ == "__main__":
    unittest.main()
