#!/usr/bin/env python3
"""Inert, content-free 24-hour evidence gate for the EXISTING Mac OmniRoute worker.

The caller must independently authenticate a consistent copied host snapshot,
the COMPLETE claimed-event ledger including the preceding rolling-day lookback,
the active host pacing policy and any separate human-review decisions. Boolean
attestations are NOT authentication. This function reads no Mac state, invokes
no models, changes no queue, and cannot prove that a host was actually online.
It never outputs private job IDs, prompts, paths, model errors or raw timestamps.
"""
from collections import deque

ROLES = ("gale", "gus", "hank", "jane", "jesse", "mike", "saul")
OUTCOMES = frozenset(("running", "model_failed", "pending_review",
                      "review_ready", "review_rejected", "review_accepted"))
MAX_HEARTBEATS = 1000
MAX_CLAIMS = 1000
DAY = 86400


def _refuse(code):
    return {"status": code, "heartbeat_coverage": "unverified",
            "claim_safety": "unverified", "claims_24h": None,
            "roles": None, "issues": [],
            "host_authenticated_by_this_function": False,
            "human_review_authenticated_by_this_function": False,
            "model_calls": 0, "queue_writes": 0, "mac_execution": False}



def _valid_route_id(value, *, model=False):
    """Only bounded opaque identifiers; never return them in audit output."""
    allowed = "-_/.:"
    return (type(value) is str and 3 <= len(value) <= (180 if model else 80)
            and all(c.isascii() and (c.isalnum() or c in allowed)
                    for c in value))


def _verified_pool_policy(policy):
    """Parse explicit immutable host-attested per-account/per-model limits.

    The caller, not this function, authenticates the provider evidence and
    the complete copied reservation ledger. Duplicate or orphan entries fail.
    """
    if type(policy) is not dict or set(policy) != {"pools", "models"}:
        return None
    pools, models = policy["pools"], policy["models"]
    if (type(pools) is not list or type(models) is not list
            or not 1 <= len(pools) <= 100
            or not 1 <= len(models) <= 200):
        return None
    pool_map, model_map = {}, {}
    for row in pools:
        if (type(row) is not dict or set(row) != {
                "pool_id", "min_interval_seconds", "max_claims_24h"}
                or not _valid_route_id(row["pool_id"])):
            return None
        key = row["pool_id"]
        if key in pool_map:
            return None
        pool_map[key] = row
    for row in models:
        if (type(row) is not dict or set(row) != {
                "pool_id", "model_id", "min_interval_seconds", "max_claims_24h"}
                or not _valid_route_id(row["pool_id"])
                or not _valid_route_id(row["model_id"], model=True)
                or row["pool_id"] not in pool_map):
            return None
        key = (row["pool_id"], row["model_id"])
        if key in model_map:
            return None
        model_map[key] = row
    for row in pools + models:
        if (type(row["min_interval_seconds"]) is not int
                or not 1 <= row["min_interval_seconds"] <= DAY
                or type(row["max_claims_24h"]) is not int
                or not 1 <= row["max_claims_24h"] <= 144):
            return None
    return pool_map, model_map


def audit(heartbeats, claims, *, window_start, window_end,
          tick_seconds=300, allowed_gap_seconds=900,
          min_claim_spacing_seconds=601, rolling_claim_limit=144,
          trusted_host_copy=False, complete_event_ledger=False,
          trusted_runtime_policy=False, trusted_human_reviews=False,
          independent_pool_mode=False, trusted_pool_reservations=False,
          pool_policy=None):
    """Assess copied public-safe heartbeat/claim metadata without side effects.

    Claims are {job_id, claimed_at, role, outcome}; include the preceding
    rolling 24h to evaluate the first in-window claim. Review outcomes require
    independent human attestation; model-generated approval is never proof.
    An observed 24h heartbeat span is not a completed soak, model inference,
    specialist improvement, approved output, or current Mac access.
    """
    if (trusted_host_copy is not True or complete_event_ledger is not True
            or trusted_runtime_policy is not True):
        return _refuse("unverified_host_ledger_or_policy")
    if type(independent_pool_mode) is not bool:
        return _refuse("invalid_pool_mode")
    if independent_pool_mode:
        if trusted_pool_reservations is not True:
            return _refuse("unverified_independent_pool_evidence")
        verified = _verified_pool_policy(pool_policy)
        if verified is None:
            return _refuse("invalid_pool_policy")
        pool_map, model_map = verified
    else:
        if trusted_pool_reservations is not False or pool_policy is not None:
            return _refuse("unexpected_pool_evidence")
        pool_map, model_map = {}, {}
    if (type(window_start) is not int or type(window_end) is not int
            or not 1700000000 <= window_start < window_end <= 4102444800
            or window_end - window_start > DAY
            or type(tick_seconds) is not int or not 30 <= tick_seconds <= 3600
            or type(allowed_gap_seconds) is not int
            or not tick_seconds <= allowed_gap_seconds <= 3600
            or type(min_claim_spacing_seconds) is not int
            or not 1 <= min_claim_spacing_seconds <= 3600
            or type(rolling_claim_limit) is not int
            or not 1 <= rolling_claim_limit <= 1000):
        return _refuse("invalid_window_or_pinned_policy")
    if (not isinstance(heartbeats, (list, tuple))
            or not isinstance(claims, (list, tuple))
            or len(heartbeats) > MAX_HEARTBEATS
            or len(claims) > MAX_CLAIMS):
        return _refuse("invalid_evidence_shape")
    if any(type(t) is not int or not window_start <= t <= window_end
           for t in heartbeats):
        return _refuse("invalid_heartbeat_evidence")
    beats = sorted(heartbeats)
    if len(set(beats)) != len(beats):
        return _refuse("duplicate_heartbeat_evidence")
    jobs = set()
    normalized = []
    for row in claims:
        expected_fields = {"job_id", "claimed_at", "role", "outcome"}
        if independent_pool_mode:
            expected_fields.update(("pool_id", "model_id"))
        if (type(row) is not dict or set(row) != expected_fields
                or type(row["job_id"]) is not str
                or not 8 <= len(row["job_id"]) <= 120
                or any(not (c.isascii() and (c.isalnum() or c in "-_"))
                       for c in row["job_id"])
                or row["job_id"] in jobs
                or type(row["claimed_at"]) is not int
                or not window_start - DAY <= row["claimed_at"] <= window_end
                or type(row["role"]) is not str or row["role"] not in ROLES
                or type(row["outcome"]) is not str
                or row["outcome"] not in OUTCOMES):
            return _refuse("invalid_or_duplicate_claim_evidence")
        if independent_pool_mode:
            if (not _valid_route_id(row["pool_id"])
                    or not _valid_route_id(row["model_id"], model=True)
                    or row["pool_id"] not in pool_map
                    or (row["pool_id"], row["model_id"]) not in model_map):
                return _refuse("invalid_or_incomplete_pool_claim_evidence")
        jobs.add(row["job_id"])
        normalized.append(row)
    if (trusted_human_reviews is not True and
            any(row["outcome"] in ("review_accepted", "review_rejected")
                for row in normalized)):
        return _refuse("human_review_evidence_unverified")

    issues = []
    if window_end - window_start < DAY:
        issues.append("heartbeat_window_short")
    if not beats or beats[0] > window_start + allowed_gap_seconds:
        issues.append("heartbeat_start_missing")
    if not beats or beats[-1] < window_end - allowed_gap_seconds:
        issues.append("heartbeat_end_missing")
    if any(b - a > allowed_gap_seconds for a, b in zip(beats, beats[1:])):
        issues.append("heartbeat_gap_exceeded")

    ordered = sorted(normalized, key=lambda row: (row["claimed_at"], row["job_id"]))
    rolling = deque()
    last_claim = None
    last_pool, last_model = {}, {}
    rolling_pool, rolling_model = {}, {}
    for row in ordered:
        stamp = row["claimed_at"]
        if independent_pool_mode:
            pool_id = row["pool_id"]
            model_key = (pool_id, row["model_id"])
            for key, limits, last, windows, prefix in (
                    (pool_id, pool_map[pool_id], last_pool,
                     rolling_pool, "pool"),
                    (model_key, model_map[model_key], last_model,
                     rolling_model, "model")):
                previous = last.get(key)
                if (previous is not None
                        and stamp - previous < limits["min_interval_seconds"]
                        and prefix + "_spacing_violation" not in issues):
                    issues.append(prefix + "_spacing_violation")
                last[key] = stamp
                window = windows.setdefault(key, deque())
                while window and window[0] <= stamp - DAY:
                    window.popleft()
                window.append(stamp)
                if (len(window) > limits["max_claims_24h"]
                        and prefix + "_rolling_cap_exceeded" not in issues):
                    issues.append(prefix + "_rolling_cap_exceeded")
        else:
            if (last_claim is not None
                    and stamp - last_claim < min_claim_spacing_seconds
                    and "claim_spacing_violation" not in issues):
                issues.append("claim_spacing_violation")
            last_claim = stamp
        while rolling and rolling[0] <= stamp - DAY:
            rolling.popleft()
        rolling.append(stamp)
        if len(rolling) > rolling_claim_limit:
            if "rolling_claim_cap_exceeded" not in issues:
                issues.append("rolling_claim_cap_exceeded")

    counts = {role: {"claims_24h": 0, "review_ready": 0,
                     "model_failed": 0, "human_accepted_attested": 0}
              for role in ROLES}
    in_window = [row for row in normalized
                 if window_start <= row["claimed_at"] <= window_end]
    for row in in_window:
        count = counts[row["role"]]
        count["claims_24h"] += 1
        if row["outcome"] == "review_ready":
            count["review_ready"] += 1
        if row["outcome"] == "model_failed":
            count["model_failed"] += 1
        if row["outcome"] == "review_accepted":
            count["human_accepted_attested"] += 1

    heartbeat_issues = any(x.startswith("heartbeat_") for x in issues)
    claim_issues = any(x in (
        "claim_spacing_violation", "rolling_claim_cap_exceeded",
        "pool_spacing_violation", "model_spacing_violation",
        "pool_rolling_cap_exceeded", "model_rolling_cap_exceeded")
        for x in issues)
    return {
        "status": "evidence_violation" if issues else "source_only_evidence_consistent",
        "heartbeat_coverage": ("insufficient" if heartbeat_issues else
                               "24h_sample_coverage_attested"),
        "claim_safety": "violation" if claim_issues else "pacing_and_cap_consistent",
        "claims_24h": len(in_window),
        "roles": counts,
        "issues": issues,
        "host_authenticated_by_this_function": False,
        "human_review_authenticated_by_this_function": False,
        "model_inference_proven_by_this_function": False,
        "continuous_specialist_improvement_proven": False,
        "model_calls": 0, "queue_writes": 0, "mac_execution": False,
    }
