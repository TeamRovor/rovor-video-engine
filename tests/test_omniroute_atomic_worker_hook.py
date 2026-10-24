"""Integration checks for existing live-worker SQLite claim + single-model route.

No endpoint calls, Mac process changes or production provider credentials.
"""
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ghost_worker as worker
import omniroute_continuous as continuous
import omniroute_fleet_binding as binding

NOW = 1000.0
MODEL = "openrouter/cohere/north-mini-code:free"
COMBO = "rovor-single-fast-free"
POOL = "openrouter_test_quota"
CATALOG = [{
    "name": COMBO, "strategy": "priority", "isHidden": False,
    "models": [{"kind": "model", "providerId": "openrouter", "model": MODEL}],
}]
ROUTES = {MODEL: {"combo": COMBO, "provider_id": "openrouter"}}


def spec(job_id):
    return {"id": job_id, "public_only": True, "minimum_tier": 1,
            "estimated_input_tokens": 1000,
            "requested_output_tokens": 200, "required_skills": ["text"]}


def model(**changes):
    value = {
        "model_id": MODEL, "quota_pool_id": POOL,
        "pool_remaining_requests": 1, "pool_verified_at": 980.0,
        "pool_inflight": 0, "pool_max_inflight": 1,
        "tier": 1, "skills": ["text"], "max_input_tokens": 8192,
        "max_output_tokens": 4096, "max_inflight": 1,
        "inflight": 0, "remaining_requests": 1,
        "latency_ms": 500, "claims_since_reset": 0,
        "success_fraction": 0.98, "health": "ready",
        "verified_at": 980.0, "cooldown_until": None,
        "quota_reset_at": 2000.0, "cost_per_request_usd": 0,
        "account_free_verified": True, "privacy_approved": True,
        "terms_approved": True, "quota_verified": True,
        "approved_model_id": True, "completed_canary_verified": True,
    }
    value.update(changes)
    return value


def fleet(job_id, **changes):
    packet = {"task": spec(job_id), "models": [model()],
              "routes": ROUTES, "catalog": CATALOG,
              "host_evidence_authenticated": True}
    packet.update(changes)
    return packet


class WorkerAtomicFleetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.workspace = Path(self.tmp.name) / "workspace"
        self.workspace.mkdir()
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)
        self.packet = next(iter(continuous.assignments()))

    def queue(self):
        return worker.enqueue(self.conn, worker.OMNI_KIND,
                              {"assignment": self.packet},
                              "test-" + str(uuid.uuid4()), now=900)

    def claim(self, job, config, *, when=NOW):
        return worker.claim(self.conn, "rovor-continuous-research", when,
            allow_omniroute_model_use=True, omniroute_queue_job_id=job,
            omni_max_24h=144, omni_continuous=True, omni_pace_seconds=601,
            omni_verified_fleet=config)

    def test_existing_job_claim_and_reservation_commit_atomically(self):
        job = self.queue()
        answer = self.claim(job, fleet(job))
        self.assertEqual(answer["omni_capacity"]["model_id"], MODEL)
        self.assertEqual(answer["omni_capacity"]["combo"], COMBO)
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "running")
        row = self.conn.execute(
            "SELECT model_id,quota_pool_id,status FROM omni_model_reservations WHERE job_id=?",
            (job,)).fetchone()
        self.assertEqual(tuple(row), (MODEL, POOL, "reserved"))

    def test_no_capacity_does_not_claim_or_consume_last_request(self):
        job = self.queue()
        x = self.claim(job, fleet(job, models=[model(remaining_requests=0)]))
        self.assertIsNone(x)
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "queued")
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM omni_model_reservations").fetchone()[0], 0)

    def test_untrusted_provider_or_paid_route_never_claimed(self):
        job = self.queue()
        for bad in (fleet(job, host_evidence_authenticated=False),
                    fleet(job, models=[model(account_free_verified=False)]),
                    fleet(job, models=[model(cost_per_request_usd=0.005)])):
            try:
                self.assertIsNone(self.claim(job, bad))
            except ValueError:
                pass
            self.assertEqual(self.conn.execute(
                "SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "queued")

    def test_queued_job_and_task_must_match_exactly(self):
        job = self.queue()
        with self.assertRaisesRegex(ValueError, "exact queued job"):
            self.claim(job, fleet(str(uuid.uuid4())))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "queued")

    def test_route_catalog_drift_rolls_back_reservation_and_claim(self):
        job = self.queue()
        mutated = [{"name": COMBO, "strategy": "priority", "isHidden": False,
                    "models": [CATALOG[0]["models"][0], CATALOG[0]["models"][0]]}]
        with self.assertRaisesRegex(ValueError, "unapproved_fallback"):
            self.claim(job, fleet(job, catalog=mutated))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0], "queued")
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='omni_model_reservations'").fetchone()[0],
            0)

    def test_no_fleet_path_preserves_original_claim_semantics(self):
        job = self.queue()
        answer = worker.claim(self.conn, "old-continuous", NOW,
            allow_omniroute_model_use=True, omniroute_queue_job_id=job,
            omni_max_24h=144, omni_continuous=True, omni_pace_seconds=601)
        self.assertEqual(answer["id"], job)
        self.assertNotIn("omni_capacity", answer)

    def test_selected_route_rechecked_before_gateway_call(self):
        with self.assertRaisesRegex(ValueError, "changed_to_multi_model"):
            binding.verify_before_completion(
                {"model_id": MODEL, "combo": COMBO, "pool_id": POOL, "provider_id": "openrouter"},
                [{"name": COMBO, "strategy": "priority", "isHidden": False,
                  "models": [CATALOG[0]["models"][0], CATALOG[0]["models"][0]]}])
        self.assertEqual(binding.verify_before_completion(
            {"model_id": MODEL, "combo": COMBO, "pool_id": POOL, "provider_id": "openrouter"}, CATALOG), COMBO)

    def test_capacity_selected_model_runs_same_public_packet_once_and_releases_slot(self):
        job = self.queue()
        calls = []
        def completion(model_id, prompt, key):
            calls.append(model_id)
            return ("Proposed publicly sourced implementation steps. "
                    "These tests are proposed rather than executed.\n" * 6,
                    {"prompt_tokens": 100, "completion_tokens": 120,
                     "total_tokens": 220})
        import omniroute_workpack_runner as workpack
        with mock.patch.object(workpack, "access_key", return_value="mocked-test-key"), \
             mock.patch.object(continuous, "latest_public_tasks", side_effect=ValueError("offline")), \
             mock.patch.object(worker, "time") as clock, \
             mock.patch.object(continuous, "execute", wraps=continuous.execute) as execution:
            # run_once relies on the actual current time for receipt metadata;
            # avoid mock clocks that affect the imported workpack module.
            clock.time.return_value = NOW
            with mock.patch.object(workpack, "http_completion", side_effect=completion), \
                 mock.patch("ghost_omniroute_job.read_combo_catalog", return_value=CATALOG):
                result = worker.run_once(self.conn, self.workspace,
                    owner="rovor-continuous-research", now=NOW,
                    allow_omniroute_model_use=True, omniroute_queue_job_id=job,
                    omni_max_24h=144, omni_continuous=True,
                    omni_pace_seconds=601, omni_verified_fleet=fleet(job))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], COMBO)
        self.assertEqual(result["result"]["selected_model_config_id"], MODEL)
        self.assertEqual(result["status"], "needs_review")
        row=self.conn.execute("SELECT status FROM omni_model_reservations WHERE job_id=?",
                              (job,)).fetchone()
        self.assertEqual(row[0], "released")

    def test_selected_provider_drift_is_rejected_even_when_model_name_same(self):
        drifted = [{
            "name": COMBO, "strategy": "priority", "isHidden": False,
            "models": [{"kind": "model", "providerId": "groq", "model": MODEL}]
        }]
        with self.assertRaisesRegex(ValueError, "selected_model_changed_before_completion"):
            binding.verify_before_completion(
                {"model_id": MODEL, "combo": COMBO,
                 "pool_id": POOL, "provider_id": "openrouter"}, drifted)

    def test_verify_binding_requires_one_exact_provider_model(self):
        self.assertEqual(binding.verify_binding(MODEL, ROUTES, CATALOG), COMBO)
        with self.assertRaises(ValueError):
            binding.verify_binding(MODEL, {MODEL: {"combo":COMBO,"provider_id":"groq"}}, CATALOG)
        with self.assertRaises(ValueError):
            binding.verify_binding(MODEL, ROUTES, [{**CATALOG[0],"isHidden":True}])

    def test_host_live_route_changed_after_reservation_never_posts(self):
        job = self.queue()
        changed = [{
            "name": COMBO, "strategy": "priority", "isHidden": False,
            "models": [CATALOG[0]["models"][0], CATALOG[0]["models"][0]]
        }]
        import omniroute_workpack_runner as workpack
        with mock.patch("ghost_omniroute_job.read_combo_catalog", return_value=changed), \
             mock.patch.object(workpack, "http_completion",
                               side_effect=AssertionError("No gateway POST permitted")) as completion:
            result = worker.run_once(self.conn, self.workspace,
                owner="rovor-continuous-research", now=NOW,
                allow_omniroute_model_use=True, omniroute_queue_job_id=job,
                omni_max_24h=144, omni_continuous=True,
                omni_pace_seconds=601, omni_verified_fleet=fleet(job))
        completion.assert_not_called()
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(self.conn.execute(
            "SELECT status FROM omni_model_reservations WHERE job_id=?",
            (job,)).fetchone()[0], "reserved")

    def test_ticked_worker_accepts_only_explicit_internal_fleet_provider(self):
        with mock.patch.object(continuous, "latest_public_tasks",
                               side_effect=ValueError("offline")), \
             mock.patch.object(worker, "run_once") as run:
            run.return_value = {"result": {"review_status": "draft_ready_for_human_review"}}
            supplied = []
            def supplier(job, payload, when):
                supplied.append(job)
                self.assertEqual(set(payload), {"assignment"})
                self.assertEqual(when, NOW)
                return fleet(job)
            output = continuous.tick(self.state, self.workspace, now=NOW,
                                     verified_fleet_provider=supplier)
        self.assertEqual(len(supplied), 1)
        self.assertTrue(output["review_ready"])
        self.assertEqual(run.call_args.kwargs["omni_verified_fleet"]["task"]["id"],
                         supplied[0])

    def independent(self, job_id, *, two_pools=False, **kw):
        fast = model(pool_remaining_requests=5, remaining_requests=5,
            pool_min_interval_seconds=120, pool_max_claims_24h=5,
            model_min_interval_seconds=60, model_max_claims_24h=5)
        models = [fast]
        routes = dict(ROUTES)
        catalog = list(CATALOG)
        if two_pools:
            backup_id = "groq/fallback/medium:free"
            backup_combo = "rovor-independent-medium"
            models.append(model(model_id=backup_id, quota_pool_id="groq_verified_pool",
                tier=2, pool_remaining_requests=5, remaining_requests=5,
                pool_min_interval_seconds=120, pool_max_claims_24h=5,
                model_min_interval_seconds=60, model_max_claims_24h=5))
            routes[backup_id] = {"combo": backup_combo, "provider_id": "groq"}
            catalog.append({"name": backup_combo, "strategy": "priority",
                "isHidden": False,
                "models": [{"kind": "model", "providerId": "groq",
                            "model": backup_id}]})
        return fleet(job_id, models=models, routes=routes, catalog=catalog,
                     independent_pool_limits=True, **kw)

    def test_other_eligible_pool_claims_immediately_while_first_job_running(self):
        first, second = self.queue(), self.queue()
        initial = self.claim(first, self.independent(first,two_pools=True))
        self.assertEqual(initial["omni_capacity"]["model_id"], MODEL)
        # Same timestamp: global 601s wait and "any job running" would reject.
        # With *verified* separate pools, the new job has an independent
        # model+account reservation and still a globally counted claim.
        followup = self.claim(second,self.independent(second,two_pools=True))
        self.assertEqual(followup["omni_capacity"]["model_id"],
                         "groq/fallback/medium:free")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0], 2)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE event='claimed'").fetchone()[0], 2)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(DISTINCT quota_pool_id) FROM omni_model_reservations"
            ).fetchone()[0], 2)

    def test_same_account_waits_even_with_unused_second_model(self):
        one, two = self.queue(),self.queue()
        self.assertIsNotNone(self.claim(one,self.independent(one)))
        self.assertIsNone(self.claim(two,self.independent(two)))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?", (two,)).fetchone()[0],"queued")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM omni_model_reservations").fetchone()[0],1)

    def test_finished_slot_still_has_independent_pool_cooldown(self):
        one,two = self.queue(),self.queue()
        self.assertIsNotNone(self.claim(one,self.independent(one)))
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(one,))
        import omniroute_model_reservation as reservation
        reservation.release_finished_slot(self.conn,one,now=NOW+1)
        self.conn.commit()
        self.assertIsNone(self.claim(two,self.independent(two),when=NOW+2))
        self.assertIsNotNone(self.claim(two,self.independent(two),when=NOW+121))

    def test_pool_rate_limit_not_refunded_by_finished_jobs(self):
        one,two=self.queue(),self.queue()
        limited=self.independent(one)
        limited["models"][0]["pool_max_claims_24h"]=1
        self.assertIsNotNone(self.claim(one,limited))
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(one,))
        import omniroute_model_reservation as reservation
        reservation.release_finished_slot(self.conn,one,now=NOW+1)
        self.conn.commit()
        again=self.independent(two)
        again["models"][0]["pool_max_claims_24h"]=1
        self.assertIsNone(self.claim(two,again,when=NOW+121))

    def test_missing_independent_rate_attestation_fails_without_claim(self):
        job=self.queue()
        modified=self.independent(job)
        del modified["models"][0]["pool_max_claims_24h"]
        with self.assertRaisesRegex(ValueError,"independent_pool_limits_unverified"):
            self.claim(job,modified)
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0],"queued")
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='omni_model_reservations'"
            ).fetchone()[0],0)

    def test_independent_pool_mode_requires_authenticated_host_evidence(self):
        job=self.queue()
        wrong=self.independent(job,host_evidence_authenticated=False)
        with self.assertRaisesRegex(ValueError,"authenticated host evidence"):
            self.claim(job,wrong)
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0],"queued")

    def test_global_failure_circuit_remains_closed_to_all_pools(self):
        job=self.queue()
        for n in range(3):
            old=self.queue()
            self.conn.execute("UPDATE jobs SET status='needs_review',result=? "
                "WHERE id=?", (json.dumps({"draft_status":
                                "needs_review_no_auto_retry"}),old))
            self.conn.execute("INSERT INTO events(job_id,event,detail,timestamp) "
                              "VALUES(?,?,?,?)",(old,"claimed","{}",NOW-3+n))
        self.assertIsNone(self.claim(job,self.independent(job,two_pools=True)))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0],"queued")

    def test_global_emergency_144_day_ceiling_still_applies(self):
        job=self.queue()
        old=self.queue()
        self.conn.execute("UPDATE jobs SET status='needs_review',result='{}' "
                          "WHERE id=?",(old,))
        self.conn.executemany("INSERT INTO events(job_id,event,detail,timestamp) "
            "VALUES(?,?,?,?)",[(old,"claimed","{}",NOW-60-j)
                                for j in range(144)])
        self.assertIsNone(self.claim(job,self.independent(job,two_pools=True)))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0],"queued")

    def test_legacy_default_still_enforces_global_spacing_even_with_model_data(self):
        first,second=self.queue(),self.queue()
        self.assertIsNotNone(self.claim(first,fleet(first)))
        # No independent flag: even a different verified model must wait.
        alternate=self.independent(second,two_pools=True)
        del alternate["independent_pool_limits"]
        self.assertIsNone(self.claim(second,alternate))

    def test_one_service_can_feed_three_distinct_verified_pool_jobs_in_a_tick(self):
        calls=[]
        def supply(job_id,payload,when):
            self.assertTrue(set(payload) == {"assignment"})
            self.assertEqual(when,NOW)
            return self.independent(job_id,two_pools=True)
        def complete(_conn,_workspace,**kwargs):
            target=kwargs["omniroute_queue_job_id"]
            self.assertTrue(kwargs["omni_verified_fleet"]["independent_pool_limits"])
            self.assertEqual(kwargs["omni_max_24h"],144)
            self.assertEqual(kwargs["omni_pace_seconds"],601)
            self.assertNotIn(target,calls)
            calls.append(target)
            _conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(target,))
            return {"result":{"review_status":"draft_ready_for_human_review"}}
        with mock.patch.object(continuous,"latest_public_tasks",
                               side_effect=ValueError("offline")):
            with mock.patch.object(worker,"run_once",side_effect=complete):
                summary=continuous.tick(self.state,self.workspace,now=NOW,
                    verified_fleet_provider=supply,max_verified_jobs_per_tick=3)
        self.assertEqual(summary["executed"],3)
        self.assertEqual(summary["review_ready_count"],3)
        self.assertEqual(len(calls),3)
        self.assertEqual(summary["dispatch_mode"],"verified_independent_pool_opt_in")
        self.assertFalse(summary["dispatch"]["model_requests_confirmed_by_heartbeat"])
        self.assertNotIn("paced_wait",json.dumps(summary))

    def test_batch_without_trusted_host_adapter_never_attempts_model(self):
        with self.assertRaisesRegex(ValueError,"trusted provider callback"):
            continuous.tick(self.state,self.workspace,now=NOW,
                            max_verified_jobs_per_tick=2)
        with mock.patch.object(worker,"run_once",
                               side_effect=AssertionError("no model allowed")) as called:
            with self.assertRaisesRegex(ValueError,"independently verified pools"):
                continuous.tick(self.state,self.workspace,now=NOW,
                    max_verified_jobs_per_tick=2,
                    verified_fleet_provider=lambda job,payload,clock:fleet(job))
        called.assert_not_called()

    def test_stop_while_batch_active_prevents_next_model(self):
        calls=[]
        def complete(_conn,_workspace,**kwargs):
            calls.append(kwargs["omniroute_queue_job_id"])
            (self.state/"STOP").touch()
            return {"result":{"review_status":"draft_ready_for_human_review"}}
        with mock.patch.object(continuous,"latest_public_tasks",
                               side_effect=ValueError("offline")):
            with mock.patch.object(worker,"run_once",side_effect=complete):
                output=continuous.tick(self.state,self.workspace,now=NOW,
                    verified_fleet_provider=lambda jid,payload,t:self.independent(jid),
                    max_verified_jobs_per_tick=5)
        self.assertEqual(len(calls),1)
        self.assertEqual(output["executed"],1)

    def test_batch_limit_is_bounded_and_boolean_rejected(self):
        for n in (True,0,10,"9",None):
            with self.subTest(bad=n):
                with self.assertRaisesRegex(ValueError,"Verified multi-pool batch"):
                    continuous.tick(self.state,self.workspace,now=NOW,
                        verified_fleet_provider=lambda job,payload,t:
                            self.independent(job), max_verified_jobs_per_tick=n)

    def test_single_verified_mode_heartbeat_does_not_claim_global_paced_wait(self):
        with mock.patch.object(continuous,"latest_public_tasks",
                               side_effect=ValueError("offline")):
            with mock.patch.object(worker,"run_once",
                return_value={"result":{"review_status":
                    "draft_ready_for_human_review"}}):
                result=continuous.tick(self.state,self.workspace,now=NOW,
                    verified_fleet_provider=lambda jid,payload,when:
                        self.independent(jid))
        self.assertEqual(result["executed"],1)
        self.assertEqual(result["dispatch_mode"],
                         "verified_independent_pool_opt_in")
        self.assertEqual(result["dispatch"]["reason"],
                         "independent_pool_capacity_checked_per_claim")

    def test_fleet_mode_cannot_run_on_legacy_unbounded_claim(self):
        job=self.queue()
        with self.assertRaisesRegex(ValueError, "requires continuous"):
            worker.claim(self.conn,"legacy",NOW,allow_omniroute_model_use=True,
                         omniroute_queue_job_id=job, omni_verified_fleet=fleet(job))


if __name__ == "__main__":
    unittest.main()
