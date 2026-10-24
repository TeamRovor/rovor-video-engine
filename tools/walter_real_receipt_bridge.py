#!/usr/bin/env python3
"""Bridge COPIED Mac SQLite OmniRoute evidence to private specialist coverage.

No SQLite connection, network, inference, queue mutation or host execution.
Caller must independently authenticate a complete copied jobs/claimed-events
ledger, role mappings, human reviews and grounded candidates. Neither model
text nor worker status can confer human approval. Never publish private inputs.
"""
import json
import math
import re

ROLES = frozenset(("mike", "jane", "jesse", "gale", "gus", "saul", "hank"))
KEY = re.compile(r"^[a-z][a-z0-9-]{7,119}$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_ROWS = 10000
MAX_RESULT_BYTES = 65536


class BridgeError(ValueError):
    """Only fixed, content-free error codes."""


def _deny(code):
    raise BridgeError(code)


def _clock(value, now):
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        _deny("invalid_private_timestamp")
    if not 1700000000 <= value <= now:
        _deny("invalid_private_timestamp")
    return int(value)


def _job_id(value):
    if type(value) is not str:
        _deny("invalid_private_job_id")
    if UUID.fullmatch(value):
        return "job-" + value.replace("-", "")
    if KEY.fullmatch(value):
        return value
    _deny("invalid_private_job_id")


def normalize_dedupe(value):
    """Preserve real SQLite 64-hex dedupe identities for coverage's key grammar."""
    if type(value) is not str:
        _deny("invalid_private_dedupe")
    if SHA.fullmatch(value):
        return "sha-" + value
    if KEY.fullmatch(value):
        return value
    _deny("invalid_private_dedupe")


def _result(raw):
    if raw is None:
        return {}
    if type(raw) is not str or len(raw.encode("utf-8", errors="replace")) > MAX_RESULT_BYTES:
        _deny("invalid_private_result")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        _deny("invalid_private_result")
    if not isinstance(data, dict):
        _deny("invalid_private_result")
    for key in ("draft_status", "review_status"):
        if key in data and type(data[key]) is not str:
            _deny("invalid_private_result")
    # Ignore private draft text, paths, error messages and model assertions.
    return data


def _status(job, result):
    status = job["status"]
    if status == "running":
        return "running"
    if status == "failed" or result.get("draft_status") == "needs_review_no_auto_retry":
        return "model_failed"
    if status != "needs_review":
        _deny("unexpected_claimed_job_status")
    if (result.get("draft_status") == "draft_completed_needs_review"
            and result.get("review_status") == "draft_ready_for_human_review"):
        return "review_ready"
    return "pending_review"


def prepare(jobs, claims, job_roles, human_reviews, candidates, *, now,
            trusted_sqlite_copy=False, trusted_role_mapping=False,
            trusted_human_reviews=False, complete_ledger=False,
            trusted_grounded_candidates=False):
    """Return private, in-memory inputs for walter_specialist_coverage.choose.

    Trust flags are caller attestations, not authentication performed here.
    Independently authenticated human review alone can change review_ready
    to review_accepted/review_rejected. Caller must recheck STOP and quota
    atomically in the EXISTING worker before dispatch.
    """
    if not all(x is True for x in (trusted_sqlite_copy, trusted_role_mapping,
                                  trusted_human_reviews, complete_ledger,
                                  trusted_grounded_candidates)):
        _deny("independent_evidence_required")
    if type(now) is not int or not 1700000000 <= now <= 4102444800:
        _deny("invalid_clock")
    if (not isinstance(jobs, (tuple, list)) or len(jobs) > MAX_ROWS
            or not isinstance(claims, (tuple, list)) or len(claims) > MAX_ROWS
            or not isinstance(human_reviews, (tuple, list)) or len(human_reviews) > MAX_ROWS
            or not isinstance(candidates, (tuple, list)) or len(candidates) > MAX_ROWS
            or not isinstance(job_roles, dict)):
        _deny("invalid_private_snapshot")
    by_id, dedupes = {}, set()
    for job in jobs:
        if (type(job) is not dict or set(job) != {
                "id", "kind", "dedupe_key", "status", "result", "updated_at"}):
            _deny("invalid_private_job_shape")
        jid = job["id"]
        safe_id = _job_id(jid)
        dedupe = normalize_dedupe(job["dedupe_key"])
        if (job["kind"] != "research.omniroute" or jid in by_id
                or dedupe in dedupes or job["status"] not in
                ("queued", "running", "failed", "needs_review")):
            _deny("duplicate_or_unsafe_private_job")
        stamp = _clock(job["updated_at"], now)
        by_id[jid] = (job, safe_id, dedupe, stamp, _result(job["result"]))
        dedupes.add(dedupe)
    by_claim = {}
    for event in claims:
        if (type(event) is not dict or set(event) != {"job_id", "event", "timestamp"}
                or event["event"] != "claimed" or event["job_id"] not in by_id
                or event["job_id"] in by_claim):
            _deny("duplicate_or_unmatched_claim")
        by_claim[event["job_id"]] = _clock(event["timestamp"], now)
    for jid, (job, _, _, _, _) in by_id.items():
        if (job["status"] == "queued") != (jid not in by_claim):
            _deny("missing_or_replayed_claim")
    if set(job_roles) != set(by_claim) or any(
            type(role) is not str or role not in ROLES for role in job_roles.values()):
        _deny("unverified_job_role_mapping")
    by_review = {}
    for review in human_reviews:
        if (type(review) is not dict or set(review) != {
                "job_id", "decision", "decided_at"}
                or review["job_id"] not in by_claim
                or review["job_id"] in by_review
                or review["decision"] not in ("accepted", "rejected")):
            _deny("invalid_independent_review")
        by_review[review["job_id"]] = review
    outcomes = []
    for jid, claimed_at in by_claim.items():
        job, safe_id, dedupe, stamp, parsed = by_id[jid]
        if stamp < claimed_at:
            _deny("invalid_private_timeline")
        status = _status(job, parsed)
        status_at = stamp
        if jid in by_review:
            review = by_review[jid]
            decision_at = _clock(review["decided_at"], now)
            if status != "review_ready" or decision_at < stamp:
                _deny("review_without_completed_draft")
            status = "review_accepted" if review["decision"] == "accepted" else "review_rejected"
            status_at = decision_at
        outcomes.append({"job_id": safe_id, "role": job_roles[jid],
                         "dedupe_key": dedupe, "claimed_at": claimed_at,
                         "status_at": status_at, "status": status})
    safe_candidates = []
    for candidate in candidates:
        if type(candidate) is not dict or set(candidate) != {
                "role", "task_id", "dedupe_key", "source_sha256", "priority"}:
            _deny("invalid_grounded_candidate")
        safe_candidates.append({**candidate,
                                "dedupe_key": normalize_dedupe(candidate["dedupe_key"])})
    return {"candidates": safe_candidates, "outcomes": outcomes,
            "seen_dedupe": frozenset(dedupes),
            "model_calls": 0, "queue_writes": 0, "mac_execution": False}
