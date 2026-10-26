#!/usr/bin/env python3
"""One SQLite-atomic model-slot reservation for the EXISTING ROVOR worker.

No scheduler, model POST, API key access, new queue, retries or native actions.
The existing ghost_worker.claim BEGIN IMMEDIATE must call this BEFORE claiming
the same queued job and COMMIT both changes together. Calling a helper after
the job claim has committed cannot provide atomic fleet capacity enforcement.

The caller MUST source model/pool attestations from trusted current Mac reads.
Boolean arguments, timestamps, and JSON are not cryptographic evidence.
"""
import math
import re
import sqlite3

from omniroute_capacity_router import decide

ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")
JOB_KIND = "research.omniroute"
VALID_TERMINAL = frozenset(("needs_review", "succeeded", "failed"))


class ReservationError(ValueError):
    """A public fixed error code; never expose prompts, receipts, provider text."""


def _reject(code):
    raise ReservationError(code)


def _locked(conn):
    if not isinstance(conn, sqlite3.Connection) or not conn.in_transaction:
        _reject("existing_sqlite_claim_transaction_required")


def _finite(value, minimum=0, maximum=1e15):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS omni_model_reservations (
          job_id TEXT PRIMARY KEY,
          model_id TEXT NOT NULL,
          quota_pool_id TEXT NOT NULL,
          reserved_at REAL NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('reserved','released')),
          released_at REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS omni_model_pool_window
        ON omni_model_reservations(quota_pool_id,reserved_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS omni_model_window
        ON omni_model_reservations(model_id,reserved_at)
    """)


def _pool_slots(models, now, *, independent_pool_limits=False):
    """Verify shared-account quota evidence cannot conflict across models."""
    if not isinstance(models, (tuple, list)) or len(models) > 32:
        _reject("model_pool_catalog_invalid")
    pools = {}
    for item in models:
        if not isinstance(item, dict):
            _reject("model_pool_catalog_invalid")
        pool_id = item.get("quota_pool_id")
        if type(pool_id) is not str or not ID.fullmatch(pool_id):
            _reject("quota_pool_identity_invalid")
        remain = item.get("pool_remaining_requests")
        inflight = item.get("pool_inflight")
        limit = item.get("pool_max_inflight")
        observed = item.get("pool_verified_at")
        if (type(remain) is not int or not 0 <= remain <= 10000000
                or type(inflight) is not int or not 0 <= inflight <= 8
                or type(limit) is not int or not 1 <= limit <= 8
                or inflight > limit or not _finite(observed, 0, now + 30)
                or now - observed > 900):
            _reject("quota_pool_evidence_invalid_or_stale")
        identity = (remain, inflight, limit, observed)
        if independent_pool_limits:
            # The "9 connections" inventory does NOT attest to account-level
            # free request ceilings. Missing or malformed host rate evidence
            # must fail closed rather than silently remove global pacing.
            pool_min = item.get("pool_min_interval_seconds")
            pool_day = item.get("pool_max_claims_24h")
            model_min = item.get("model_min_interval_seconds")
            model_day = item.get("model_max_claims_24h")
            if (type(pool_min) is not int or not 1 <= pool_min <= 86400
                    or type(pool_day) is not int or not 1 <= pool_day <= 144
                    or type(model_min) is not int or not 1 <= model_min <= 86400
                    or type(model_day) is not int or not 1 <= model_day <= 144):
                _reject("independent_pool_limits_unverified")
            identity += (pool_min, pool_day)
        if pool_id in pools and pools[pool_id] != identity:
            _reject("quota_pool_conflicting_snapshots")
        pools[pool_id] = identity
    return pools


def reserve(conn, job_id, task, models, *, now,
            stop_present=True, failure_circuit_open=True,
            host_evidence_authenticated=False,
            independent_pool_limits=False):
    """Atomic proposal and capacity hold inside EXISTING BEGIN IMMEDIATE.

    Never calls the gateway. Caller must claim the exact same queued job and
    persist the selected model/route in this transaction before any POST.
    On ROLLBACK no model quota has been consumed locally.

    Every reservation is counted as a potentially spent provider request until
    the host acquires a *new* authenticated quota snapshot. Releasing a slot
    does not restore its previous request allowance.
    """
    _locked(conn)
    if not _finite(now):
        _reject("clock_invalid")
    if stop_present is not False:
        _reject("stop_requested_or_unknown")
    if failure_circuit_open is not False:
        _reject("failure_circuit_open_or_unknown")
    if host_evidence_authenticated is not True:
        _reject("host_evidence_not_authenticated")
    if type(independent_pool_limits) is not bool:
        _reject("independent_pool_limits_invalid")
    if type(job_id) is not str or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", job_id):
        _reject("existing_job_identity_invalid")
    row = conn.execute("SELECT kind,status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None or row[0] != JOB_KIND or row[1] != "queued":
        _reject("existing_queued_omniroute_job_required")
    # All submitted job IDs must be first-time reservations. A prior
    # expired/failed/finished reservation never becomes an automatic replay.
    _schema(conn)
    if conn.execute("SELECT 1 FROM omni_model_reservations WHERE job_id=?",
                    (job_id,)).fetchone():
        _reject("job_already_reserved_no_replay")

    pool_evidence = _pool_slots(
        models, now, independent_pool_limits=independent_pool_limits)
    effective = []
    pool_candidates = {}
    for item in models:
        ident, pool_id = item.get("model_id"), item["quota_pool_id"]
        # Basic shape and account scope validated by decide(), but query only
        # with parameterized SQL after validating the model identifier.
        if (not isinstance(ident, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{2,159}", ident)):
            _reject("model_identity_invalid")
        pool_remaining, pool_active, pool_max, pool_at = pool_evidence[pool_id][:4]
        model_at = item.get("verified_at")
        if not _finite(model_at, 0, now + 30):
            _reject("model_snapshot_invalid")
        used_model = conn.execute(
            "SELECT COUNT(*) FROM omni_model_reservations "
            "WHERE model_id=? AND reserved_at>=?", (ident, model_at)).fetchone()[0]
        used_pool = conn.execute(
            "SELECT COUNT(*) FROM omni_model_reservations "
            "WHERE quota_pool_id=? AND reserved_at>=?", (pool_id, pool_at)).fetchone()[0]
        active_model = conn.execute(
            "SELECT COUNT(*) FROM omni_model_reservations "
            "WHERE model_id=? AND status='reserved'", (ident,)).fetchone()[0]
        active_pool = conn.execute(
            "SELECT COUNT(*) FROM omni_model_reservations "
            "WHERE quota_pool_id=? AND status='reserved'", (pool_id,)).fetchone()[0]
        slot = dict(item)
        # Treat host-observed and locally reserved in-flight counters as
        # overlapping measurements: max is safe for one installed worker.
        slot["inflight"] = max(slot.get("inflight", 0), active_model)
        slot["remaining_requests"] = max(
            0, slot.get("remaining_requests", 0) - used_model)
        # Shared provider accounts need both per-model and aggregate headroom.
        if max(pool_active, active_pool) >= pool_max:
            slot["remaining_requests"] = 0
        slot["remaining_requests"] = min(
            slot["remaining_requests"], max(0, pool_remaining - used_pool))
        if independent_pool_limits:
            # Both provider/account and exact-model windows are enforced
            # *inside* the existing BEGIN IMMEDIATE, including completed and
            # failed attempts. A different eligible pool may replace a busy
            # model immediately, while the same exhausted pool must wait.
            pool_min, pool_day = pool_evidence[pool_id][4:]
            model_min, model_day = (item["model_min_interval_seconds"],
                                    item["model_max_claims_24h"])
            cutoff = now - 86400
            model_window = conn.execute(
                "SELECT COUNT(*),MAX(reserved_at) FROM omni_model_reservations "
                "WHERE model_id=? AND reserved_at>=?",
                (ident, cutoff)).fetchone()
            pool_window = conn.execute(
                "SELECT COUNT(*),MAX(reserved_at) FROM omni_model_reservations "
                "WHERE quota_pool_id=? AND reserved_at>=?",
                (pool_id, cutoff)).fetchone()
            if model_window[0] >= model_day or pool_window[0] >= pool_day:
                slot["remaining_requests"] = 0
            for last_at, minimum in ((model_window[1], model_min),
                                     (pool_window[1], pool_min)):
                if last_at is not None and last_at + minimum > now:
                    slot["cooldown_until"] = max(
                        slot["cooldown_until"] or 0, last_at + minimum)
        effective.append(slot)
        pool_candidates[ident] = pool_id

    decision = decide(task, effective, now=now,
                      stop_requested=False, failure_circuit_open=False)
    model = decision["chosen_model_id"]
    if model is None:
        return dict(decision, existing_sqlite_claim_transaction=True,
                    model_request_posted=False)
    pool_id = pool_candidates[model]
    # The INSERT is serialized with the existing job claim BEGIN IMMEDIATE.
    conn.execute(
        "INSERT INTO omni_model_reservations "
        "(job_id,model_id,quota_pool_id,reserved_at,status,released_at) "
        "VALUES(?,?,?,?,?,NULL)",
        (job_id, model, pool_id, now, "reserved"))
    return {"status": "reserved_existing_job_slot_only",
            "job_id": job_id, "chosen_model_id": model,
            "quota_pool_id": pool_id,
            "existing_sqlite_claim_transaction": True,
            "model_request_posted": False,
            "queue_claimed_by_this_helper": False,
            "automatic_retry_allowed": False,
            "reservation_must_commit_with_existing_job_claim": True}


def release_finished_slot(conn, job_id, *, now):
    """Release concurrency only after terminal state; NEVER refund quota."""
    _locked(conn)
    if not _finite(now):
        _reject("clock_invalid")
    reservation = conn.execute(
        "SELECT status,reserved_at FROM omni_model_reservations WHERE job_id=?",
        (job_id,)).fetchone()
    if reservation is None or reservation[0] != "reserved":
        _reject("active_reservation_not_found")
    job = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if job is None or job[0] not in VALID_TERMINAL:
        _reject("terminal_job_evidence_required")
    if now < reservation[1]:
        _reject("clock_invalid")
    conn.execute("UPDATE omni_model_reservations "
                 "SET status='released',released_at=? "
                 "WHERE job_id=? AND status='reserved'",
                 (now, job_id))
    return {"status": "inflight_slot_released_request_remains_counted",
            "job_id": job_id, "quota_refunded": False,
            "automatic_retry_allowed": False}
