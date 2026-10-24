#!/usr/bin/env python3
"""Select ONE inert, source-grounded specialist proposal using trusted outcomes.

This is not an OmniRoute client, worker, quota reserver, scheduler, or reviewer.
The caller MUST independently authenticate: (1) all candidates against a pinned
public Git tree and the existing grounding gate, (2) outcomes against private
SQLite jobs and independent human reviews, and (3) the full seen-dedupe ledger.
Neither this helper nor an LLM can confer those attestations. The caller must
also perform STOP, global pacing, quota, provider and atomic claim checks AGAIN
at dispatch. No private draft text, paths or provider errors are returned.
"""
from collections import Counter
import re

ROLES = ("gale", "gus", "hank", "jane", "jesse", "mike", "saul")
ROLE_SET = frozenset(ROLES)
KEY = re.compile(r"^[a-z][a-z0-9-]{7,119}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
STATUSES = frozenset(("running", "model_failed", "pending_review",
                      "review_ready", "review_rejected", "review_accepted"))
PENDING = frozenset(("running", "pending_review", "review_ready"))
FAILED = frozenset(("model_failed", "review_rejected"))
WINDOW = 86400
COOLDOWN = 3600
MAX_PENDING_PER_ROLE = 2
MAX_PENDING_GLOBAL = 7
MAX_ROWS = 10000


class CoverageError(ValueError):
    """Fixed, content-free rejection code."""


def _deny(code):
    raise CoverageError(code)


def _key(value):
    return type(value) is str and KEY.fullmatch(value) is not None


def _validate(candidates, outcomes, seen_dedupe, now):
    if type(now) is not int or not 1700000000 <= now <= 4102444800:
        _deny("invalid_clock")
    if (not isinstance(candidates, (list, tuple)) or len(candidates) > MAX_ROWS
            or not isinstance(outcomes, (list, tuple)) or len(outcomes) > MAX_ROWS
            or not isinstance(seen_dedupe, (set, frozenset))
            or len(seen_dedupe) > 100000 or any(not _key(x) for x in seen_dedupe)):
        _deny("invalid_ledger_shape")
    seen_candidates = set()
    seen_tasks = set()
    for c in candidates:
        if (type(c) is not dict or set(c) != {
                "role", "task_id", "dedupe_key", "source_sha256", "priority"}
                or type(c["role"]) is not str or c["role"] not in ROLE_SET
                or not _key(c["task_id"])
                or not _key(c["dedupe_key"])
                or type(c["source_sha256"]) is not str
                or SHA.fullmatch(c["source_sha256"]) is None
                or type(c["priority"]) is not int or not 1 <= c["priority"] <= 5):
            _deny("invalid_grounded_candidate")
        if c["dedupe_key"] in seen_candidates or c["task_id"] in seen_tasks:
            _deny("duplicate_grounded_candidate")
        seen_candidates.add(c["dedupe_key"])
        seen_tasks.add(c["task_id"])
    jobs = set()
    dedupes = set()
    for row in outcomes:
        if (type(row) is not dict or set(row) != {
                "job_id", "role", "dedupe_key", "claimed_at", "status_at", "status"}
                or not _key(row["job_id"]) or type(row["role"]) is not str
                or row["role"] not in ROLE_SET
                or not _key(row["dedupe_key"])
                or type(row["claimed_at"]) is not int
                or not 1700000000 <= row["claimed_at"] <= now
                or type(row["status_at"]) is not int
                or not row["claimed_at"] <= row["status_at"] <= now
                or type(row["status"]) is not str or row["status"] not in STATUSES):
            _deny("invalid_outcome_record")
        if row["job_id"] in jobs or row["dedupe_key"] in dedupes:
            _deny("duplicate_or_replayed_outcome")
        jobs.add(row["job_id"])
        dedupes.add(row["dedupe_key"])
        if row["dedupe_key"] not in seen_dedupe:
            _deny("incomplete_seen_ledger")
    return None


def choose(candidates, outcomes, *, now, seen_dedupe=None,
           trusted_candidates=False, trusted_outcomes=False,
           authoritative_ledger=False, stop_present=True,
           other_job_running=True, owner_opt_in=False):
    """Return one *unsubmitted* candidate and bounded, content-free role counts.

    Fairness is by attempted jobs in the rolling day, then oldest role claim,
    then approved task priority. Review-ready drafts count as outstanding until
    independently accepted/rejected. Two consecutive recent failures pause the
    role for one hour (no automatic retry); other roles can continue. This is
    a policy proposal, not a replacement for the host's global safety gates.
    """
    if stop_present is not False:
        return {"status": "stopped", "candidate": None}
    if (trusted_candidates is not True or trusted_outcomes is not True
            or authoritative_ledger is not True or owner_opt_in is not True
            or other_job_running is not False):
        return {"status": "unverified_authority", "candidate": None}
    _validate(candidates, outcomes, seen_dedupe, now)
    if any(row["status"] == "running" for row in outcomes):
        return {"status": "running_outcome_requires_reconciliation",
                "candidate": None, "model_calls": 0, "queue_writes": 0}
    counts = {role: Counter() for role in ROLES}
    last = {role: -1 for role in ROLES}
    recent = {role: [] for role in ROLES}
    for row in outcomes:
        role = row["role"]
        when = row["claimed_at"]
        status = row["status"]
        if status in PENDING:
            counts[role]["awaiting_review"] += 1
        if when >= now - WINDOW:
            counts[role]["attempts_24h"] += 1
            if status in FAILED:
                counts[role]["failed_24h"] += 1
            if status == "review_accepted":
                counts[role]["accepted_24h"] += 1
        if row["status_at"] >= now - WINDOW:
            recent[role].append((row["status_at"], row["job_id"], status))
        last[role] = max(last[role], when)
    cooldown = set()
    for role in ROLES:
        ordered = sorted(recent[role], key=lambda row: (row[0], row[1]))
        # Use independently verified status timestamps, not claim timestamps:
        # a long-running job may fail hours after its initial claim.
        if len(ordered) >= 2 and ordered[-1][2] in FAILED and ordered[-2][2] in FAILED:
            if now - ordered[-1][0] < COOLDOWN:
                cooldown.add(role)
    summary = {role: {
        "attempts_24h": counts[role]["attempts_24h"],
        "awaiting_review": counts[role]["awaiting_review"],
        "failed_24h": counts[role]["failed_24h"],
        "accepted_24h": counts[role]["accepted_24h"],
        "failure_cooldown": role in cooldown,
    } for role in ROLES}
    if sum(counts[role]["awaiting_review"] for role in ROLES) >= MAX_PENDING_GLOBAL:
        return {"status": "global_review_backpressure", "candidate": None,
                "coverage": summary, "model_calls": 0, "queue_writes": 0}
    unseen = [c for c in candidates if c["dedupe_key"] not in seen_dedupe]
    eligible = [c for c in unseen if c["role"] not in cooldown
                and counts[c["role"]]["awaiting_review"] < MAX_PENDING_PER_ROLE]
    if not eligible:
        if not unseen:
            reason = "no_unattempted_candidates"
        elif all(c["role"] in cooldown for c in unseen):
            reason = "failure_cooldown"
        elif all(counts[c["role"]]["awaiting_review"] >= MAX_PENDING_PER_ROLE
                 for c in unseen):
            reason = "role_review_backpressure"
        else:
            reason = "no_eligible_candidate"
        return {"status": reason, "candidate": None, "coverage": summary,
                "model_calls": 0, "queue_writes": 0}
    chosen = min(eligible, key=lambda c: (
        counts[c["role"]]["attempts_24h"], last[c["role"]],
        c["priority"], c["role"], c["task_id"], c["dedupe_key"]))
    return {"status": "candidate_only_not_enqueued",
            "candidate": dict(chosen), "coverage": summary,
            "requires_atomic_sqlite_claim": True,
            "requires_independent_review": True,
            "model_calls": 0, "queue_writes": 0}
