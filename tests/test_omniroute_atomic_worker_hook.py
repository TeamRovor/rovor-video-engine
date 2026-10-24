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
                {"model_id": MODEL, "combo": COMBO, "pool_id": POOL},
                [{"name": COMBO, "strategy": "priority", "isHidden": False,
                  "models": [CATALOG[0]["models"][0], CATALOG[0]["models"][0]]}])
        self.assertEqual(binding.verify_before_completion(
            {"model_id": MODEL, "combo": COMBO, "pool_id": POOL}, CATALOG), COMBO)

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

    def test_verify_binding_requires_one_exact_provider_model(self):
        self.assertEqual(binding.verify_binding(MODEL, ROUTES, CATALOG), COMBO)
        with self.assertRaises(ValueError):
            binding.verify_binding(MODEL, {MODEL: {"combo":COMBO,"provider_id":"groq"}}, CATALOG)
        with self.assertRaises(ValueError):
            binding.verify_binding(MODEL, ROUTES, [{**CATALOG[0],"isHidden":True}])

    def test_fleet_mode_cannot_run_on_legacy_unbounded_claim(self):
        job=self.queue()
        with self.assertRaisesRegex(ValueError, "requires continuous"):
            worker.claim(self.conn,"legacy",NOW,allow_omniroute_model_use=True,
                         omniroute_queue_job_id=job, omni_verified_fleet=fleet(job))


if __name__ == "__main__":
    unittest.main()
