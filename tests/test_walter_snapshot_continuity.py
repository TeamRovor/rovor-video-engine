"""Offline cross-shift continuity tests: no host, SQLite or model calls."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_snapshot_continuity import compare

START = 1800000000


def job(ident="job-gale-001", at=START + 1200, role="gale",
        outcome="running", pool=None, model=None):
    return {"job_id": ident, "claimed_at": at, "role": role,
            "outcome": outcome, "pool_id": pool, "model_id": model}


def fixture():
    old = {"captured_at": START + 3600, "retained_from": START,
           "jobs": [job()], "heartbeats": list(range(START, START + 3601, 300))}
    new = {"captured_at": START + 7200, "retained_from": START + 900,
           "jobs": [job(), job("job-mike-002", START + 4200, "mike")],
           "heartbeats": list(range(START + 900, START + 7201, 300))}
    return old, new


def check(old=None, new=None, **kwargs):
    if old is None or new is None:
        old, new = fixture()
    flags = dict(trusted_previous=True, trusted_current=True,
                 complete_previous=True, complete_current=True)
    flags.update(kwargs)
    return compare(old, new, **flags)


class ContinuityTests(unittest.TestCase):
    def test_unchanged_overlap_with_new_claim_and_heartbeats(self):
        result = check()
        self.assertEqual(result["status"], "source_only_continuity_consistent")
        self.assertEqual(result["new_jobs"], 1)
        self.assertEqual(result["new_heartbeats"], 12)
        self.assertFalse(result["host_authenticated_by_this_function"])
        self.assertEqual(result["model_calls"], 0)

    def test_does_not_mutate_private_inputs(self):
        old, new = fixture()
        before = copy.deepcopy((old, new))
        check(old, new)
        self.assertEqual((old, new), before)

    def test_missing_claim_detected(self):
        old, new = fixture()
        new["jobs"] = new["jobs"][1:]
        self.assertIn("previous_claim_disappeared", check(old, new)["issues"])

    def test_missing_heartbeat_detected(self):
        old, new = fixture()
        new["heartbeats"].remove(START + 1800)
        self.assertIn("previous_heartbeat_disappeared", check(old, new)["issues"])

    def test_backfilled_claim_detected(self):
        old, new = fixture()
        new["jobs"].append(job("job-jane-003", START + 2000, "jane"))
        self.assertIn("backfilled_unseen_claim", check(old, new)["issues"])

    def test_backfilled_heartbeat_detected(self):
        old, new = fixture()
        old["heartbeats"].remove(START + 1800)
        self.assertIn("backfilled_unseen_heartbeat", check(old, new)["issues"])

    def test_claim_identity_changes_detected(self):
        for key, value in (("claimed_at", START + 1300), ("role", "jane"),
                           ("pool_id", "pool-a"), ("model_id", "model-a")):
            with self.subTest(key=key):
                old, new = fixture()
                if key in ("pool_id", "model_id"):
                    old["jobs"][0]["pool_id"] = "pool-a"
                    old["jobs"][0]["model_id"] = "model-a"
                    new["jobs"][0]["pool_id"] = "pool-a"
                    new["jobs"][0]["model_id"] = "model-a"
                    value = "pool-b" if key == "pool_id" else "model-b"
                new["jobs"][0][key] = value
                self.assertIn("immutable_claim_identity_changed",
                              check(old, new)["issues"])

    def test_valid_review_advances_only_with_human_attestation(self):
        old, new = fixture()
        old["jobs"][0]["outcome"] = "review_ready"
        new["jobs"][0]["outcome"] = "review_accepted"
        self.assertEqual(check(old, new)["status"],
                         "unverified_human_review_history")
        result = check(old, new, trusted_human_reviews=True)
        self.assertEqual(result["advanced_reviews"], 1)
        self.assertEqual(result["status"], "source_only_continuity_consistent")
        self.assertFalse(result["human_review_authenticated_by_this_function"])

    def test_pending_to_ready_allowed_without_human_approval(self):
        old, new = fixture()
        old["jobs"][0]["outcome"] = "pending_review"
        new["jobs"][0]["outcome"] = "review_ready"
        self.assertEqual(check(old, new)["status"],
                         "source_only_continuity_consistent")

    def test_running_to_accepted_is_invalid_even_if_trusted(self):
        old, new = fixture()
        new["jobs"][0]["outcome"] = "review_accepted"
        self.assertIn("invalid_outcome_transition",
                      check(old, new, trusted_human_reviews=True)["issues"])

    def test_terminal_failure_cannot_recover_by_replaying(self):
        old, new = fixture()
        old["jobs"][0]["outcome"] = "model_failed"
        new["jobs"][0]["outcome"] = "running"
        self.assertIn("invalid_outcome_transition", check(old, new)["issues"])

    def test_terminal_review_cannot_regress(self):
        old, new = fixture()
        old["jobs"][0]["outcome"] = "review_accepted"
        new["jobs"][0]["outcome"] = "review_ready"
        self.assertIn("invalid_outcome_transition",
                      check(old, new, trusted_human_reviews=True)["issues"])

    def test_expired_old_history_is_not_a_false_disappearance(self):
        old, new = fixture()
        new["retained_from"] = START + 2700
        new["jobs"] = new["jobs"][1:]
        new["heartbeats"] = [x for x in new["heartbeats"] if x >= START + 2700]
        self.assertNotIn("previous_claim_disappeared", check(old, new)["issues"])

    def test_insufficient_overlap_fails_closed(self):
        old, new = fixture()
        new["retained_from"] = old["captured_at"] - 899
        new["jobs"] = [x for x in new["jobs"]
                       if x["claimed_at"] >= new["retained_from"]]
        new["heartbeats"] = [x for x in new["heartbeats"]
                             if x >= new["retained_from"]]
        self.assertEqual(check(old, new)["status"], "insufficient_history_overlap")

    def test_no_new_heartbeat_detects_stalled_evidence(self):
        old, new = fixture()
        new["heartbeats"] = [x for x in new["heartbeats"] if x <= START + 3600]
        self.assertIn("heartbeat_progress_missing", check(old, new)["issues"])

    def test_untrusted_snapshots_refused(self):
        for key in ("trusted_previous", "trusted_current",
                    "complete_previous", "complete_current"):
            with self.subTest(key=key):
                self.assertEqual(check(**{key: False})["status"],
                                 "unverified_snapshot_provenance")

    def test_capture_time_must_move_forward(self):
        old, new = fixture()
        new["captured_at"] = old["captured_at"]
        new["jobs"] = [x for x in new["jobs"]
                       if x["claimed_at"] <= new["captured_at"]]
        new["heartbeats"] = [x for x in new["heartbeats"]
                             if x <= new["captured_at"]]
        self.assertEqual(check(old, new)["status"], "invalid_snapshot_order")

    def test_capture_gap_cannot_exceed_day(self):
        old, new = fixture()
        new["captured_at"] = old["captured_at"] + 86401
        self.assertEqual(check(old, new)["status"], "invalid_snapshot_order")

    def test_duplicate_job_and_heartbeat_rejected(self):
        old, new = fixture()
        new["jobs"].append(copy.deepcopy(new["jobs"][0]))
        self.assertEqual(check(old, new)["status"], "invalid_snapshot_shape")
        old, new = fixture()
        new["heartbeats"].append(new["heartbeats"][0])
        self.assertEqual(check(old, new)["status"], "invalid_snapshot_shape")

    def test_bad_shape_or_private_identifier_refused(self):
        for key, value in (("job_id", "../private"), ("claimed_at", True),
                           ("role", "walter"), ("outcome", "auto_approved")):
            with self.subTest(key=key):
                old, new = fixture()
                new["jobs"][0][key] = value
                self.assertEqual(check(old, new)["status"], "invalid_snapshot_shape")

    def test_model_pool_pair_required(self):
        old, new = fixture()
        new["jobs"][0]["pool_id"] = "pool-a"
        self.assertEqual(check(old, new)["status"], "invalid_snapshot_shape")

    def test_incomplete_shared_heartbeat_refused(self):
        old, new = fixture()
        old["heartbeats"] = [START, START + 300]
        self.assertEqual(check(old, new)["status"],
                         "insufficient_shared_heartbeat_evidence")

    def test_results_never_expose_private_ids_routes_or_timestamps(self):
        old, new = fixture()
        for row in old["jobs"] + new["jobs"]:
            row["pool_id"], row["model_id"] = "account-secret", "model-secret"
        result = check(old, new)
        for secret in ("job-gale-001", "account-secret", "model-secret",
                       str(START)):
            self.assertNotIn(secret, repr(result))

    def test_lookback_expansion_not_mistaken_for_backfill(self):
        old, new = fixture()
        old["retained_from"] = START + 900
        old["heartbeats"] = old["heartbeats"][3:]
        new["retained_from"] = START
        new["heartbeats"] = list(range(START, START + 7201, 300))
        new["jobs"].append(job("job-older-003", START + 100))
        self.assertNotIn("backfilled_unseen_claim", check(old, new)["issues"])

    def test_unverified_review_in_old_snapshot_refused(self):
        old, new = fixture()
        old["jobs"][0]["outcome"] = "review_rejected"
        new["jobs"][0]["outcome"] = "review_rejected"
        self.assertEqual(check(old, new)["status"],
                         "unverified_human_review_history")


if __name__ == "__main__":
    unittest.main()
