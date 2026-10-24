"""Telemetry tests use disposable SQLite/heartbeat; never real Mac or AI."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_workforce_telemetry as telemetry

NOW = 500000.0
MODEL = "openrouter/cohere/north-mini-code:free"
SECRET = "PRIVATE_WORKER_RESPONSE_SHOULD_NEVER_APPEAR"


class WorkforceTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.state = Path(self.folder.name) / "state"
        self.state.mkdir()
        self.db = self.state / "jobs.sqlite3"
        self.conn = sqlite3.connect(str(self.db))
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                result TEXT);
            CREATE TABLE events (
                id INTEGER PRIMARY KEY, job_id TEXT, event TEXT, timestamp REAL);
        """)

    def record(self, id, status, draft=None, review=None, claimed=NOW - 100):
        details = ({"draft_status": draft, "review_status": review,
                    "receipt": "/private/user/SENSITIVE",
                    "private": SECRET} if draft else None)
        self.conn.execute("INSERT INTO jobs(id,kind,status,result) VALUES(?,?,?,?)",
                          (id, "research.omniroute", status,
                           json.dumps(details) if details else None))
        if claimed is not None:
            self.conn.execute(
                "INSERT INTO events(job_id,event,timestamp) VALUES(?,?,?)",
                (id, "claimed", claimed))
        self.conn.commit()

    def reservations(self):
        self.conn.executescript("""
            CREATE TABLE omni_model_reservations (
                job_id TEXT PRIMARY KEY,model_id TEXT NOT NULL,
                quota_pool_id TEXT NOT NULL,reserved_at REAL NOT NULL,
                status TEXT NOT NULL,released_at REAL);
        """)

    def hold(self, job, model=MODEL, status="reserved"):
        self.conn.execute(
            "INSERT INTO omni_model_reservations VALUES(?,?,?,?,?,?)",
            (job, model, "PRIVATE_ACCOUNT_ID", NOW-100, status,
             NOW-50 if status == "released" else None))
        self.conn.commit()

    def test_no_reservation_table_means_no_fleet_use_proof(self):
        self.record("a", "needs_review", "draft_completed_needs_review",
                    "draft_ready_for_human_review")
        self.record("b", "needs_review", "needs_review_no_auto_retry",
                    "failed_needs_review")
        result = telemetry.inspect(self.state, now=NOW)
        self.assertFalse(result["model_reservation_table_present"])
        self.assertFalse(result["all_configured_models_covered"])
        self.assertEqual(result["models_with_reservation_evidence"], [])
        self.assertEqual(result["claims_last_24h"], 2)
        self.assertEqual(result["review_ready_drafts_total"], 1)
        self.assertEqual(result["claims_without_model_reservation_last_24h"], 2)
        self.assertFalse(result["provider_http_completions_verified_by_this_probe"])
        self.assertFalse(result["human_accepted_outputs_verified"])

    def test_nonready_review_is_not_success(self):
        self.record("a", "needs_review", "needs_review_no_auto_retry")
        self.record("b", "needs_review", "draft_completed_needs_review",
                    "failed_needs_review")
        self.record("c", "needs_review", "draft_completed_needs_review",
                    "draft_ready_for_human_review")
        out = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(out["review_ready_drafts_total"], 1)
        self.assertEqual(out["all_jobs_by_evidence_state"], {
            "draft_ready_for_human_review": 1,
            "model_attempt_not_review_ready": 1,
            "pending_or_failed_review": 1,
        })
        self.assertNotIn(SECRET, json.dumps(out))
        self.assertNotIn("/private/user", json.dumps(out))

    def test_claimed_is_not_equivalent_to_model_post_or_human_approval(self):
        self.record("a", "queued", claimed=None)
        self.record("b", "running")
        self.record("c", "needs_review",
                    "draft_completed_needs_review", "draft_ready_for_human_review")
        result = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(result["claims_last_24h"], 2)
        self.assertEqual(result["last_24h_claimed_jobs_by_current_evidence_state"],
                         {"draft_ready_for_human_review": 1, "running": 1})
        self.assertEqual(result["review_ready_drafts_total"], 1)
        self.assertFalse(result["provider_http_completions_verified_by_this_probe"])

    def test_one_model_reservation_is_not_proof_it_was_response_provider(self):
        self.record("a", "needs_review", "draft_completed_needs_review",
                    "draft_ready_for_human_review")
        self.reservations()
        self.hold("a", status="released")
        output = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(output["claims_with_model_reservation_last_24h"], 1)
        self.assertEqual(output["claims_without_model_reservation_last_24h"], 0)
        self.assertEqual(output["inflight_reservations_held"], 0)
        m = output["models_with_reservation_evidence"]
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["model_id"], MODEL)
        self.assertEqual(m[0]["jobs_draft_ready_for_human_review"], 1)
        self.assertFalse(m[0]["responding_upstream_model_verified"])
        self.assertNotIn("PRIVATE_ACCOUNT_ID", json.dumps(output))

    def test_model_slot_held_after_failed_job_is_visible_not_a_success(self):
        self.record("a", "needs_review", "needs_review_no_auto_retry")
        self.reservations()
        self.hold("a")
        output = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(output["inflight_reservations_held"], 1)
        self.assertEqual(output["models_with_reservation_evidence"][0]
                         ["jobs_model_attempt_not_review_ready"], 1)
        self.assertEqual(output["review_ready_drafts_total"], 0)

    def test_malformed_model_identity_never_enters_status(self):
        self.record("a", "running")
        self.reservations()
        self.hold("a", model="SENSITIVE_BAD_MODEL_ID")
        output = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(output["models_with_reservation_evidence"], [])
        self.assertEqual(output["reserved_jobs_total"], 1)
        self.assertNotIn("SENSITIVE_BAD_MODEL_ID", json.dumps(output))

    def test_heartbeat_is_bounded_whitelisted_and_stale_flagged(self):
        self.record("a", "running")
        (self.state/"continuous-status.json").write_text(json.dumps({
            "observed_at": NOW-90, "status": "tick_complete", "executed": 1,
            "review_ready": False,
            "feed": "existing_queue",
            "dispatch": {"reason": "no_queued_work", "queued": 0,
                         "private_error": SECRET},
            "secret": SECRET,
        }))
        info = telemetry.inspect(self.state, now=NOW)
        self.assertTrue(info["heartbeat"]["recent"])
        self.assertEqual(info["heartbeat"]["last_tick_feed"], "existing_queue")
        self.assertEqual(info["heartbeat"]["last_tick_dispatch_reason"], "no_queued_work")
        self.assertFalse(info["heartbeat"]["last_tick_review_ready_draft"])
        self.assertNotIn(SECRET, json.dumps(info))
        older = telemetry.inspect(self.state, now=NOW+1300)
        self.assertFalse(older["heartbeat"]["recent"])

    def test_unsafe_symlinked_heartbeat_is_ignored(self):
        private = Path(self.folder.name)/"private-data.txt"
        private.write_text(SECRET)
        (self.state/"continuous-status.json").symlink_to(private)
        out=telemetry.inspect(self.state, now=NOW)
        self.assertEqual(out["heartbeat"], {"available": False, "recent": False})
        self.assertNotIn(SECRET, json.dumps(out))

    def test_repeated_claim_events_do_not_inflate_job_count(self):
        self.record("a", "running")
        self.conn.execute(
            "INSERT INTO events(job_id,event,timestamp) VALUES(?,?,?)",
            ("a", "claimed", NOW-30))
        self.conn.commit()
        out = telemetry.inspect(self.state, now=NOW)
        self.assertEqual(out["claims_last_24h"], 2)
        self.assertEqual(out["distinct_claimed_jobs_last_24h"], 1)

    def test_old_claim_not_counted_in_current_day(self):
        self.record("a", "needs_review", "draft_completed_needs_review",
                    "draft_ready_for_human_review", claimed=NOW-90000)
        out=telemetry.inspect(self.state,now=NOW)
        self.assertEqual(out["claims_last_24h"],0)
        self.assertEqual(out["review_ready_drafts_total"],1)
        self.assertIsNone(out["last_claim_at"])

    def test_corrupt_or_missing_snapshot_fails_closed_without_content(self):
        absent=Path(self.folder.name)/"nonexistent"
        self.assertEqual(telemetry.main(["--state",str(absent)]),2)

    def test_heartbeat_future_or_invalid_not_echoed(self):
        self.record("a","running")
        (self.state/"continuous-status.json").write_text(
            json.dumps({"observed_at":NOW+10000,
                        "feed":{"unexpected":SECRET}}))
        out=telemetry.inspect(self.state,now=NOW)
        self.assertEqual(out["heartbeat"], {"available": False, "recent": False})


if __name__=="__main__":
    unittest.main()
