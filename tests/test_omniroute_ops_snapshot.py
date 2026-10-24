"""Tests for one-command OmniRoute operations report; all inputs synthetic."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_ops_snapshot as ops

NOW = 1792833466.0
SECRET = "SECRET-PRIVATE-RAW-TEXT-NEVER-ECHO"
A = "openrouter/cohere/north-mini-code:free"
B = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
C = "openrouter/nvidia/nemotron-3.5-super-vl:free"


def combo(name, ids):
    return {"name": name, "strategy": "priority", "models": [
        {"kind": "model", "providerId": "openrouter", "model": mid}
        for mid in ids]}


class Completed:
    def __init__(self, data, code=0):
        self.returncode = code
        self.stdout = data if isinstance(data, bytes) else data.encode()
        self.stderr = ("error: " + SECRET).encode()


class FakeCLI:
    def __init__(self, broken=None):
        self.calls = []
        self.broken = broken
        self.data = {
            ("--version",): Completed("3.8.52\n"),
            ("providers", "list", "--json"): Completed(
                "Loaded env from PRIVATE_PATH\n" + json.dumps({"connections": [
                    {"type": t, "key": SECRET} for t in
                    ["cohere", "gemini", "groq", "mistral", "nvidia", "openrouter",
                     "sensitive-enterprise-provider", "other", "other"]]})),
            ("combo", "list", "--json"): Completed(json.dumps({"combos": [
                combo("rovor-fast-free-v1", [A, C]),
                combo("rovor-code-free-v1", [A, B]),
                combo("rovor-reason-free-v1", [B, C]),
                combo("rovor-vision-free-v1", [C]),
                combo("user-private-secret-" + SECRET, [B]),
            ]})),
            ("models", "--json"): Completed(json.dumps({"models": [
                {"id": A, "description": SECRET}, {"id": B, "key": SECRET},
                {"id": C, "login": SECRET}, {"id": "unrelated/test:paid"}]})),
            ("quota", "status", "--json"): Completed(
                json.dumps({"status": "healthy", "raw_key": SECRET,
                            "billing_account": SECRET})),
        }

    def __call__(self, argv, **kw):
        self.calls.append(tuple(argv[1:]))
        assert kw.get("capture_output") is True
        assert kw.get("check") is False
        assert kw.get("input") == b""
        assert kw.get("timeout", 1000) <= 8
        if tuple(argv[1:]) == self.broken:
            return Completed(b"INACCESSIBLE", 1)
        return self.data.get(tuple(argv[1:]), Completed("unavailable", 1))


class TestOneShot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.state.mkdir()
        self.db = self.state / "jobs.sqlite3"
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY, kind TEXT, status TEXT, result TEXT)")
            con.execute("CREATE TABLE events(id INTEGER PRIMARY KEY, job_id TEXT, event TEXT, timestamp REAL)")
            n=0
            for category, count in (("ready", 10), ("failed", 12), ("pending", 5)):
                for _ in range(count):
                    ident = "job-" + str(n)
                    if category == "ready":
                        outcome = {"draft_status": "draft_completed_needs_review",
                                   "review_status": "draft_ready_for_human_review"}
                    elif category == "failed":
                        outcome = {"draft_status": "needs_review_no_auto_retry"}
                    else:
                        outcome = {"draft_status": "draft_completed_needs_review",
                                   "review_status": "failed_needs_review"}
                    outcome.update({"prompt": SECRET, "receipt": "/private/" + SECRET})
                    con.execute("INSERT INTO jobs VALUES (?,?,?,?)",
                                (ident, "research.omniroute", "needs_review",
                                 json.dumps(outcome)))
                    con.execute("INSERT INTO events(job_id,event,timestamp) VALUES (?,?,?)",
                                (ident, "claimed", NOW-200))
                    n += 1
            con.execute("INSERT INTO jobs VALUES(?,?,?,NULL)",
                        ("job-queue", "research.omniroute", "queued"))
        (self.state / "continuous-status.json").write_text(json.dumps({
            "observed_at": NOW-136, "status": "tick_complete",
            "feed": "new_public_task_assignment_queued", "executed": 0,
            "dispatch": {"reason": "paced_wait", "queued": 1,
                         "provider-secret": SECRET}}))

    def test_realistic_27_claim_9_connection_3_model_report(self):
        fake = FakeCLI()
        value = ops.inspect(self.state, "/mock/omniroute", now=NOW, run=fake)
        self.assertEqual(value["cli_version"], "3.8.52")
        self.assertEqual(value["worker"]["claims_last_24h"], 27)
        self.assertEqual(value["worker"]["review_ready_drafts_total"], 10)
        self.assertEqual(value["worker"]["outcomes_total"]["model_attempt_not_review_ready"], 12)
        self.assertEqual(value["worker"]["outcomes_total"]["pending_or_failed_review"], 5)
        self.assertEqual(value["worker"]["outcomes_total"]["queued"], 1)
        self.assertEqual(value["recent_review_ready_rate_percent"], 37)
        self.assertEqual(value["fleet"]["distinct_routed_models"], 3)
        self.assertEqual(value["fleet"]["rovor_combo_count"], 4)
        self.assertEqual(value["providers"]["entries"], 9)
        self.assertEqual(value["model_catalogue"]["catalogue_distinct_model_ids"], 4)
        self.assertTrue(value["worker"]["heartbeat"]["recent"])
        self.assertEqual(value["priority"], "improve_draft_readiness_before_increasing_claim_rate")
        self.assertFalse(value["quota"]["zero_cost_entitlement_verified"])
        self.assertFalse(value["nine_verified_active_models"])
        self.assertNotIn(SECRET, json.dumps(value))
        self.assertNotIn("/private/", json.dumps(value))

    def test_cli_invokes_only_inventory_version_and_quota_reads(self):
        fake=FakeCLI()
        ops.inspect(self.state, "/mock/omniroute", now=NOW, run=fake)
        self.assertEqual(set(fake.calls), {
            ("--version",), ("providers", "list", "--json"),
            ("combo", "list", "--json"), ("models", "--json"),
            ("quota", "status", "--json")})
        self.assertFalse(any("complete" in x or "ensure" in x or
                             "add" in x or "chat" in x for cmd in fake.calls for x in cmd))

    def test_unavailable_model_inventory_and_quota_stay_unknown(self):
        fake=FakeCLI()
        fake.data.pop(("models", "--json"))
        fake.data.pop(("quota", "status", "--json"))
        value=ops.inspect(self.state, "/mock/omniroute", now=NOW, run=fake)
        self.assertEqual(value["model_catalogue"]["status"], "unavailable_or_unknown_shape")
        self.assertEqual(value["quota"]["status"], "unavailable_or_unexpected_shape")
        self.assertIn(("quota", "--json"), fake.calls)
        self.assertFalse(value["quota"]["ready_for_auto_fallback"])

    def test_quota_readable_never_implies_zero_cost(self):
        fake=FakeCLI()
        fake.data[("quota","status","--json")] = Completed(
            json.dumps({"free":True, "remaining":10000, "account":SECRET}))
        value=ops.inspect(self.state,"/mock/omniroute",now=NOW,run=fake)
        self.assertEqual(value["quota"]["status"], "readable_unverified_content")
        self.assertFalse(value["quota"]["zero_cost_entitlement_verified"])
        self.assertNotIn(SECRET,json.dumps(value))

    def test_fails_closed_without_private_worker_db(self):
        result=ops.inspect(Path(self.tmp.name)/"missing","/fake",now=NOW,run=FakeCLI())
        self.assertEqual(result["worker"]["status"],"snapshot_unavailable")
        self.assertEqual(result["priority"],"restore_read_only_worker_visibility")
        self.assertEqual(result["worker"]["heartbeat"],{"available":False})

    def test_symlinked_worker_db_and_heartbeat_unavailable(self):
        (self.state/"continuous-status.json").unlink()
        (self.state/"continuous-status.json").symlink_to(self.db)
        self.assertEqual(ops._heartbeat(self.state, now=NOW),{"available":False})
        self.db.unlink()
        self.db.symlink_to(Path(self.tmp.name)/"missing-target")
        self.assertEqual(ops._sqlite_snapshot(self.state,now=NOW),
                         {"status":"snapshot_unavailable"})

    def test_model_paid_suffix_never_marked_approved(self):
        combos={"combos":[combo("rovor-fast-free-v1",["openrouter/provider/model:paid"])]}
        view=ops._routes(combos)
        self.assertFalse(view["combos"]["rovor-fast-free-v1"]["free_suffix_only"])
        self.assertFalse(view["free_account_billing_verified"])

    def test_unknown_provider_type_hidden_and_grouped_as_other(self):
        view=ops._connections({"connections":[
            {"provider":SECRET},{"type":"groq"},{"type":"groq"}]})
        self.assertEqual(view["provider_type_counts"],{"groq":2,"other":1})
        self.assertNotIn(SECRET,json.dumps(view))

    def test_invalid_or_duplicate_rovor_combo_blocks_fleet(self):
        self.assertIsNone(ops._routes({"combos":[
            combo("rovor-fast-free-v1",[A]),combo("rovor-fast-free-v1",[B])]}))
        self.assertIsNone(ops._routes({"combos":[combo("rovor-bad!route",[A])]}))

    def test_claim_events_do_not_equal_unique_requests(self):
        with sqlite3.connect(self.db) as con:
            con.execute("INSERT INTO events(job_id,event,timestamp) VALUES(?,?,?)",
                        ("job-0","claimed",NOW-100))
        view=ops._sqlite_snapshot(self.state,now=NOW)
        self.assertEqual(view["claims_last_24h"],28)
        self.assertEqual(view["distinct_claimed_jobs_last_24h"],27)
        self.assertFalse(view["human_accepted_deliverables_verified"])

    def test_live_wal_worker_is_readable_without_touching_authoritative_files(self):
        # Recreate macOS worker SQLite WAL with committed, uncheckpointed jobs.
        # A separate live connection keeps the WAL sidecar present.
        writer = sqlite3.connect(self.db)
        try:
            self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            writer.execute("INSERT INTO jobs VALUES(?,?,?,NULL)",
                           ("job-wal-new", "research.omniroute", "queued"))
            writer.commit()
            wal = self.state / "jobs.sqlite3-wal"
            self.assertTrue(wal.is_file())
            before = {name: ops._safe_db_signature(self.state / name)
                      for name in ("jobs.sqlite3", "jobs.sqlite3-wal")}
            result = ops._sqlite_snapshot(self.state, now=NOW)
            after = {name: ops._safe_db_signature(self.state / name)
                     for name in ("jobs.sqlite3", "jobs.sqlite3-wal")}
            self.assertEqual(result["status"], "consistent_read_only_snapshot")
            self.assertEqual(result["claims_last_24h"], 27)
            self.assertEqual(result["outcomes_total"]["queued"], 2)
            self.assertEqual(before, after)
        finally:
            writer.close()

    def test_wal_or_shared_memory_redirect_is_blocked(self):
        for sidecar in ("jobs.sqlite3-wal", "jobs.sqlite3-shm"):
            with self.subTest(sidecar=sidecar):
                pointer = self.state / sidecar
                pointer.symlink_to(Path(self.tmp.name) / "private-target")
                self.assertEqual(ops._sqlite_snapshot(self.state, now=NOW),
                                 {"status":"snapshot_unavailable"})
                pointer.unlink()

    def test_active_wal_snapshot_never_claims_actual_model_usage(self):
        live = sqlite3.connect(self.db)
        try:
            live.execute("PRAGMA journal_mode=WAL")
            live.execute("INSERT INTO jobs VALUES (?,?,?,NULL)",
                         ("wal-job-2", "research.omniroute", "queued"))
            live.commit()
            report = ops.inspect(self.state, "/mock", now=NOW, run=FakeCLI())
            self.assertEqual(report["worker"]["status"], "consistent_read_only_snapshot")
            self.assertEqual(report["priority"], "improve_draft_readiness_before_increasing_claim_rate")
            self.assertFalse(report["nine_verified_active_models"])
            self.assertEqual(report["recent_review_ready_rate_percent"], 37)
        finally:
            live.close()

    def test_no_completed_provider_posts_are_claimed(self):
        data=ops.inspect(self.state,"/mock",now=NOW,run=FakeCLI())
        self.assertEqual(data["gateway_completion_requests"],0)
        self.assertFalse(data["service_or_queue_modified"])
        self.assertFalse(data["worker"]["all_nine_models_used_verified"])
        self.assertFalse(data["fleet"]["working_model_completions_verified"])

    def test_heartbeat_with_unexpected_nested_input_is_not_ever_echoed(self):
        (self.state/"continuous-status.json").write_text(json.dumps({
            "observed_at":NOW-4,"feed":{"secret":SECRET},
            "dispatch":{"reason":{"secret":SECRET}}}))
        view=ops._heartbeat(self.state,now=NOW)
        self.assertNotIn(SECRET,json.dumps(view))
        self.assertEqual(view["last_tick_feed"],"unknown")
        self.assertEqual(view["last_tick_dispatch"],"unknown")

if __name__=="__main__":
    unittest.main()
