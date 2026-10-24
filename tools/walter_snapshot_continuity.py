#!/usr/bin/env python3
"""Read-only cross-shift continuity checks for copied OmniRoute evidence.

Two independently authenticated, consistently copied PRIVATE snapshots are
required. Caller attestations are not authentication. This module neither
reads SQLite nor proves that a Mac, scheduler, model or reviewer ran. Never
publish input snapshots: job identifiers and account routes are private.
"""
import re

MIN_EPOCH = 1700000000
MAX_EPOCH = 4102444800
MAX_ROWS = 1000
MAX_ELAPSED = 86400
MIN_OVERLAP = 900
ROLES = frozenset(("gale", "gus", "hank", "jane", "jesse", "mike", "saul"))
OUTCOMES = frozenset(("running", "pending_review", "review_ready",
                      "model_failed", "review_accepted", "review_rejected"))
REVIEWED = frozenset(("review_accepted", "review_rejected"))
TRANSITIONS = {
    "running": frozenset(("running", "pending_review", "review_ready",
                          "model_failed")),
    "pending_review": frozenset(("pending_review", "review_ready",
                                 "review_rejected")),
    "review_ready": frozenset(("review_ready", "review_accepted",
                              "review_rejected")),
    "model_failed": frozenset(("model_failed",)),
    "review_accepted": frozenset(("review_accepted",)),
    "review_rejected": frozenset(("review_rejected",)),
}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{8,120}$")
ROUTE = re.compile(r"^[A-Za-z0-9_./:-]{3,180}$")


def _refuse(code):
    return {"status": code, "issues": [], "new_jobs": None,
            "advanced_reviews": None, "new_heartbeats": None,
            "host_authenticated_by_this_function": False,
            "human_review_authenticated_by_this_function": False,
            "model_calls": 0, "queue_writes": 0, "mac_execution": False}


def _parse(snapshot):
    """Return normalized maps or None; reject malformed and duplicate rows."""
    if type(snapshot) is not dict or set(snapshot) != {
            "captured_at", "retained_from", "jobs", "heartbeats"}:
        return None
    captured, retained = snapshot["captured_at"], snapshot["retained_from"]
    if (type(captured) is not int or type(retained) is not int
            or not MIN_EPOCH <= retained <= captured <= MAX_EPOCH):
        return None
    jobs, heartbeats = snapshot["jobs"], snapshot["heartbeats"]
    if (type(jobs) is not list or type(heartbeats) is not list
            or len(jobs) > MAX_ROWS or len(heartbeats) > MAX_ROWS):
        return None
    normalized = {}
    for row in jobs:
        if (type(row) is not dict or set(row) != {
                "job_id", "claimed_at", "role", "outcome", "pool_id", "model_id"}):
            return None
        job_id, at = row["job_id"], row["claimed_at"]
        pool, model = row["pool_id"], row["model_id"]
        if (type(job_id) is not str or IDENTIFIER.fullmatch(job_id) is None
                or job_id in normalized or type(at) is not int
                or not retained <= at <= captured
                or type(row["role"]) is not str or row["role"] not in ROLES
                or type(row["outcome"]) is not str
                or row["outcome"] not in OUTCOMES
                or (pool is None) != (model is None)
                or (pool is not None and (
                    type(pool) is not str or ROUTE.fullmatch(pool) is None
                    or type(model) is not str or ROUTE.fullmatch(model) is None))):
            return None
        normalized[job_id] = row
    beats = set()
    for at in heartbeats:
        if type(at) is not int or not retained <= at <= captured or at in beats:
            return None
        beats.add(at)
    return captured, retained, normalized, beats


def compare(previous, current, *, trusted_previous=False,
            trusted_current=False, complete_previous=False,
            complete_current=False, trusted_human_reviews=False):
    """Check append-only continuity across consecutive private host snapshots.

    The overlap may slide as old history expires, but must include >=15 minutes
    of previously observed time. No source of trust is established here.
    Invalid inputs fail closed. Valid but inconsistent inputs produce bounded
    issue codes only, never job IDs, timestamps, provider IDs or raw drafts.
    """
    if (trusted_previous is not True or trusted_current is not True
            or complete_previous is not True or complete_current is not True):
        return _refuse("unverified_snapshot_provenance")
    old, new = _parse(previous), _parse(current)
    if old is None or new is None:
        return _refuse("invalid_snapshot_shape")
    old_at, old_from, old_jobs, old_beats = old
    new_at, new_from, new_jobs, new_beats = new
    if not old_at < new_at <= old_at + MAX_ELAPSED:
        return _refuse("invalid_snapshot_order")
    if new_from > old_at - MIN_OVERLAP:
        return _refuse("insufficient_history_overlap")
    if (any(row["outcome"] in REVIEWED for row in old_jobs.values())
            or any(row["outcome"] in REVIEWED for row in new_jobs.values())):
        if trusted_human_reviews is not True:
            return _refuse("unverified_human_review_history")
    shared_from = max(old_from, new_from)
    if not any(shared_from <= beat <= old_at for beat in old_beats):
        return _refuse("insufficient_shared_heartbeat_evidence")

    issues = set()
    for job_id, old_row in old_jobs.items():
        if old_row["claimed_at"] < new_from:
            continue  # Explicitly expired outside the current retained window.
        next_row = new_jobs.get(job_id)
        if next_row is None:
            issues.add("previous_claim_disappeared")
            continue
        for key in ("claimed_at", "role", "pool_id", "model_id"):
            if next_row[key] != old_row[key]:
                issues.add("immutable_claim_identity_changed")
                break
        if next_row["outcome"] not in TRANSITIONS[old_row["outcome"]]:
            issues.add("invalid_outcome_transition")
    new_job_count = 0
    for job_id, row in new_jobs.items():
        if job_id in old_jobs:
            continue
        if old_from <= row["claimed_at"] <= old_at:
            issues.add("backfilled_unseen_claim")
        elif row["claimed_at"] > old_at:
            new_job_count += 1
    for beat in old_beats:
        if beat >= new_from and beat not in new_beats:
            issues.add("previous_heartbeat_disappeared")
    for beat in new_beats:
        if old_from <= beat <= old_at and beat not in old_beats:
            issues.add("backfilled_unseen_heartbeat")
    new_beat_count = sum(beat > old_at for beat in new_beats)
    if not new_beat_count:
        issues.add("heartbeat_progress_missing")
    review_advances = sum(
        old_jobs[job_id]["outcome"] not in REVIEWED
        and row["outcome"] in REVIEWED
        and row["outcome"] in TRANSITIONS[old_jobs[job_id]["outcome"]]
        for job_id, row in new_jobs.items() if job_id in old_jobs)
    return {
        "status": ("evidence_violation" if issues else
                   "source_only_continuity_consistent"),
        "issues": sorted(issues),
        "new_jobs": new_job_count,
        "advanced_reviews": review_advances,
        "new_heartbeats": new_beat_count,
        "host_authenticated_by_this_function": False,
        "human_review_authenticated_by_this_function": False,
        "model_calls": 0, "queue_writes": 0, "mac_execution": False,
    }
