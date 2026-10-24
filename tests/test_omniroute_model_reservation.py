"""SQLite reservation tests: no model/network or real Mac writes."""
from concurrent.futures import ThreadPoolExecutor
import copy
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import omniroute_model_reservation as ledger

NOW = 200000.0

def task(**kw):
    value={"id":"omniroute_test_01", "public_only":True, "minimum_tier":1,
           "required_skills":["text"],"estimated_input_tokens":500,
           "requested_output_tokens":100}
    value.update(kw)
    return value

def model(name="openrouter/free/fast:free", pool="rovor_openrouter_pool", **changes):
    value={"model_id":name,"quota_pool_id":pool,
           "pool_remaining_requests":1,"pool_verified_at":NOW-20,
           "pool_inflight":0,"pool_max_inflight":1,
           "tier":1,"max_input_tokens":8192,
           "max_output_tokens":2048,"max_inflight":1,"inflight":0,
           "remaining_requests":1,"latency_ms":120,
           "claims_since_reset":0,"skills":["text","code"],
           "health":"ready","success_fraction":0.98,
           "verified_at":NOW-20,"quota_reset_at":NOW+900,
           "cooldown_until":None,
           "account_free_verified":True,
           "privacy_approved":True,"terms_approved":True,
           "quota_verified":True,"approved_model_id":True,
           "completed_canary_verified":True,"cost_per_request_usd":0}
    value.update(changes)
    return value

def connect(db):
    con=sqlite3.connect(str(db),timeout=10,isolation_level=None)
    con.execute("PRAGMA busy_timeout=10000")
    con.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,kind TEXT NOT NULL,status TEXT NOT NULL)")
    return con

def enroll(con,n=1):
    ids=[str(uuid.uuid4()) for _ in range(n)]
    con.executemany("INSERT INTO jobs(id,kind,status) VALUES(?,?,?)",
                    [(j,"research.omniroute","queued") for j in ids])
    return ids

def reserve(con,job,models=None,**kwargs):
    args={"now":NOW,"stop_present":False,"failure_circuit_open":False,
          "host_evidence_authenticated":True}
    args.update(kwargs)
    return ledger.reserve(con,job,task(),
                          models if models is not None else [model()],**args)

class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"jobs.sqlite3"
        self.conn=connect(self.db)
        self.addCleanup(self.conn.close)

    def test_reserve_needs_existing_claim_transaction(self):
        job=enroll(self.conn)[0]
        with self.assertRaisesRegex(ledger.ReservationError,"transaction_required"):
            reserve(self.conn,job)

    def test_reserve_and_claim_same_atomic_transaction(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        out=reserve(self.conn,job)
        self.assertEqual(out["chosen_model_id"],model()["model_id"])
        self.assertFalse(out["model_request_posted"])
        self.assertFalse(out["automatic_retry_allowed"])
        self.conn.execute("UPDATE jobs SET status='running' WHERE id=?",(job,))
        self.conn.commit()
        self.assertEqual(self.conn.execute("SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0],"running")
        self.assertEqual(self.conn.execute("SELECT status FROM omni_model_reservations WHERE job_id=?",(job,)).fetchone()[0],"reserved")

    def test_rollback_leaves_no_spent_allowance(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        self.assertEqual(reserve(self.conn,job)["status"],"reserved_existing_job_slot_only")
        self.conn.rollback()
        self.assertIsNone(self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='omni_model_reservations'").fetchone())
        self.conn.execute("BEGIN IMMEDIATE")
        self.assertEqual(reserve(self.conn,job)["chosen_model_id"],model()["model_id"])
        self.conn.rollback()

    def test_unique_job_never_replayed_after_release(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,job)
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(job,))
        released=ledger.release_finished_slot(self.conn,job,now=NOW+1)
        self.assertFalse(released["quota_refunded"])
        self.conn.commit()
        self.conn.execute("UPDATE jobs SET status='queued' WHERE id=?",(job,))
        self.conn.execute("BEGIN IMMEDIATE")
        with self.assertRaisesRegex(ledger.ReservationError,"job_already_reserved_no_replay"):
            reserve(self.conn,job)
        self.conn.rollback()

    def test_failed_job_must_complete_before_slot_release(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,job)
        with self.assertRaisesRegex(ledger.ReservationError,"terminal_job_evidence_required"):
            ledger.release_finished_slot(self.conn,job,now=NOW+1)
        self.conn.execute("UPDATE jobs SET status='running' WHERE id=?",(job,))
        with self.assertRaisesRegex(ledger.ReservationError,"terminal_job_evidence_required"):
            ledger.release_finished_slot(self.conn,job,now=NOW+2)
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(job,))
        self.assertEqual(ledger.release_finished_slot(self.conn,job,now=NOW+2)["status"],
                         "inflight_slot_released_request_remains_counted")
        self.conn.commit()

    def test_no_quota_refund_when_job_finishes(self):
        first,second=enroll(self.conn,2)
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,first)
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(first,))
        ledger.release_finished_slot(self.conn,first,now=NOW+1)
        x=reserve(self.conn,second)
        self.assertIsNone(x["chosen_model_id"])
        self.assertEqual(x["current_model_health"][model()["model_id"]],
                         "provider_quota_exhausted")
        self.conn.commit()

    def test_model_reenters_after_fresh_confirmed_reset(self):
        a,b=enroll(self.conn,2)
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,a)
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(a,))
        ledger.release_finished_slot(self.conn,a,now=NOW+1)
        stale=model(pool_remaining_requests=1,remaining_requests=1,verified_at=NOW-20,pool_verified_at=NOW-20)
        self.assertIsNone(reserve(self.conn,b,[stale])["chosen_model_id"])
        fresh=model(pool_remaining_requests=1,remaining_requests=1,verified_at=NOW+10,pool_verified_at=NOW+10)
        x=reserve(self.conn,b,[fresh],now=NOW+20)
        self.assertEqual(x["chosen_model_id"],fresh["model_id"])
        self.conn.commit()

    def test_shared_account_two_models_cannot_double_spend_final_request(self):
        a,b=enroll(self.conn,2)
        fast=model()
        deep=model("openrouter/free/deep:free",tier=2)
        self.conn.execute("BEGIN IMMEDIATE")
        chosen=reserve(self.conn,a,[fast,deep])
        self.assertEqual(chosen["chosen_model_id"],fast["model_id"])
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(a,))
        ledger.release_finished_slot(self.conn,a,now=NOW+1)
        x=reserve(self.conn,b,[fast,deep])
        self.assertIsNone(x["chosen_model_id"])
        self.conn.commit()

    def test_different_eligible_account_is_new_task_fallback(self):
        a,b=enroll(self.conn,2)
        preferred=model()
        fallback=model("groq/free/medium:free",pool="rovor_groq_pool",tier=2)
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,a,[preferred,fallback])
        x=reserve(self.conn,b,[preferred,fallback])
        self.assertEqual(x["chosen_model_id"],fallback["model_id"])
        self.assertEqual(x["quota_pool_id"],"rovor_groq_pool")
        self.conn.commit()

    def test_bad_or_conflicting_shared_pool_attestation_blocks_all(self):
        job=enroll(self.conn)[0]
        a=model()
        b=model("openrouter/free/other:free",pool_remaining_requests=5)
        self.conn.execute("BEGIN IMMEDIATE")
        with self.assertRaisesRegex(ledger.ReservationError,"conflicting_snapshots"):
            reserve(self.conn,job,[a,b])
        with self.assertRaisesRegex(ledger.ReservationError,"quota_pool_identity_invalid"):
            reserve(self.conn,job,[model(pool="x")])
        self.conn.rollback()

    def test_global_stop_and_failure_circuit_fail_closed(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        for arg,code in (("stop_present","stop_requested"),
                         ("failure_circuit_open","failure_circuit_open"),
                         ("host_evidence_authenticated","host_evidence_not_authenticated")):
            with self.subTest(arg=arg):
                with self.assertRaisesRegex(ledger.ReservationError,code):
                    reserve(self.conn,job,**{arg:True if arg!="host_evidence_authenticated" else False})
        self.conn.rollback()

    def test_paid_or_unverified_model_is_not_reserved(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        for changed in ({"cost_per_request_usd":.0001},
                        {"quota_verified":False},
                        {"account_free_verified":False},
                        {"completed_canary_verified":False}):
            with self.subTest(changed=changed):
                x=reserve(self.conn,job,[model(**changed)])
                self.assertIsNone(x["chosen_model_id"])
        self.conn.rollback()

    def test_private_tasks_blocked_even_with_verified_model(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        with self.assertRaisesRegex(ValueError,"task_invalid_or_not_public"):
            ledger.reserve(self.conn,job,task(public_only=False),[model()],now=NOW,
                           stop_present=False,failure_circuit_open=False,
                           host_evidence_authenticated=True)
        self.conn.rollback()

    def test_never_lease_from_wrong_job_kind_or_terminal_state(self):
        job=enroll(self.conn)[0]
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute("UPDATE jobs SET kind='files.inventory' WHERE id=?",(job,))
        with self.assertRaisesRegex(ledger.ReservationError,"existing_queued_omniroute_job_required"):
            reserve(self.conn,job)
        self.conn.execute("UPDATE jobs SET kind='research.omniroute',status='needs_review' WHERE id=?",(job,))
        with self.assertRaisesRegex(ledger.ReservationError,"existing_queued_omniroute_job_required"):
            reserve(self.conn,job)
        self.conn.rollback()

    def test_concurrent_final_allowance_on_existing_sqlite_write_lock(self):
        one,two=enroll(self.conn,2)
        def race(job):
            con=connect(self.db)
            try:
                con.execute("BEGIN IMMEDIATE")
                value=reserve(con,job)
                if value["chosen_model_id"]:
                    con.execute("UPDATE jobs SET status='running' WHERE id=?",(job,))
                con.commit()
                return value["chosen_model_id"]
            finally:
                con.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(race,(one,two)))
        self.assertEqual(sum(x is not None for x in results),1)

    def test_one_slot_not_auto_released_on_expired_lease(self):
        first,second=enroll(self.conn,2)
        m=model(remaining_requests=5,pool_remaining_requests=5)
        self.conn.execute("BEGIN IMMEDIATE")
        reserve(self.conn,first,[m])
        self.conn.execute("UPDATE jobs SET status='needs_review' WHERE id=?",(first,))
        # Uncertain/expired attempt must require explicit review, not auto
        # free the per-model active slot from just elapsed wall time.
        x=reserve(self.conn,second,[m],now=NOW+3600)
        self.assertIsNone(x["chosen_model_id"])
        self.conn.rollback()

if __name__=="__main__":
    unittest.main()
