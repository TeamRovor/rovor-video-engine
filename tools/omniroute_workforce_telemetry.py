#!/usr/bin/env python3
"""ROVOR read-only, receipt-honest OmniRoute workforce metrics for a local HUD.

Counts completed, review-ready *drafts* separately from claimed requests;
no raw model outputs, prompts, keys, arbitrary errors or private paths escape.
No AI calls, local service actions, model selection or SQLite writes.
"""
from collections import Counter
import argparse
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time

from omniroute_dispatch_pacing import snapshot

MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._:/-]{2,159}$")
KINDS = ("queued", "running", "needs_review", "failed", "succeeded")
FEEDS = ("existing_queue", "new_public_task_assignment_queued",
         "distinct_assignment_queued", "catalogue_exhausted_new_work_required",
         "stop_requested")
REASONS = ("stop_requested", "failure_circuit_requires_review",
           "existing_work_running", "no_queued_work", "rolling_quota",
           "paced_wait", "eligible",
           "independent_pool_capacity_checked_per_claim")


def valid_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _outcome(text):
    # The current worker stores a compact internal result; never echo any of it.
    if type(text) is not str or len(text) > 65536:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _category(status, outcome):
    if status == "queued":
        return "queued"
    if status == "running":
        return "running"
    if status == "failed" or outcome.get("draft_status") == "needs_review_no_auto_retry":
        return "model_attempt_not_review_ready"
    if (status == "needs_review"
            and outcome.get("draft_status") == "draft_completed_needs_review"
            and outcome.get("review_status") == "draft_ready_for_human_review"):
        return "draft_ready_for_human_review"
    if status == "needs_review":
        return "pending_or_failed_review"
    if status == "succeeded":
        # This is not a human acceptance proof.
        return "unexpected_succeeded_status"
    return "unknown_status"


def collect(conn, *, now=None):
    """Extract aggregate evidence from an already-consistent local SQLite copy."""
    now = time.time() if now is None else now
    if not valid_number(now):
        raise ValueError("invalid clock")

    totals = Counter()
    job_groups = {}
    for row in conn.execute(
            "SELECT id,status,result FROM jobs WHERE kind='research.omniroute'"):
        outcome = _outcome(row[2] if row[2] is not None else "")
        category = _category(row[1], outcome)
        job_groups[row[0]] = category
        totals[category] += 1

    observed = conn.execute(
        "SELECT e.job_id,e.timestamp FROM events e "
        "JOIN jobs j ON j.id=e.job_id "
        "WHERE j.kind='research.omniroute' AND e.event='claimed' "
        "AND e.timestamp<=? AND e.timestamp>=?",
        (now, now - 86400)).fetchall()
    claims_24h = len(observed)
    recent_ids = {row[0] for row in observed}
    last_claim_at = max((row[1] for row in observed), default=None)
    recent_categories = Counter(job_groups.get(job_id, "unknown_status")
                                for job_id in recent_ids)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    has_fleet = "omni_model_reservations" in tables
    by_model = {}
    reservations_total = 0
    active_reservations = 0
    matched_recent = set()
    if has_fleet:
        for row in conn.execute(
                "SELECT r.job_id,r.model_id,r.status,j.status,j.result "
                "FROM omni_model_reservations r LEFT JOIN jobs j ON j.id=r.job_id"):
            job_id, ident, state, job_status, saved = row
            reservations_total += 1
            if state == "reserved":
                active_reservations += 1
            # Unknown/invalid IDs must not enter a public graph.
            if type(ident) is not str or not MODEL_ID.fullmatch(ident):
                continue
            info = by_model.setdefault(ident, Counter())
            info["reserved_jobs_total"] += 1
            if state == "reserved":
                info["inflight_slots_held"] += 1
            if job_id in recent_ids:
                matched_recent.add(job_id)
                info["claims_last_24h_with_reservation"] += 1
            outcome = _outcome(saved if saved is not None else "")
            group = _category(job_status, outcome)
            info["jobs_" + group] += 1
    return {
        "schema_version": 1,
        "evidence": "consistent_local_sqlite_snapshot",
        "observation_only": True,
        "inference_requests_sent_by_probe": 0,
        "sqlite_or_launchagent_modified": False,
        "snapshot_at": now,
        "claims_last_24h": claims_24h,
        "distinct_claimed_jobs_last_24h": len(recent_ids),
        "last_claim_at": last_claim_at,
        "all_jobs_by_evidence_state": dict(sorted(totals.items())),
        "last_24h_claimed_jobs_by_current_evidence_state":
            dict(sorted(recent_categories.items())),
        "review_ready_drafts_total": totals["draft_ready_for_human_review"],
        "human_accepted_outputs_verified": False,
        "provider_http_completions_verified_by_this_probe": False,
        "model_reservation_table_present": has_fleet,
        "reserved_jobs_total": reservations_total,
        "inflight_reservations_held": active_reservations,
        "claims_with_model_reservation_last_24h": len(matched_recent),
        "claims_without_model_reservation_last_24h":
            len(recent_ids - matched_recent),
        "models_with_reservation_evidence": [
            {"model_id": key, **dict(sorted(counts.items())),
             "responding_upstream_model_verified": False,
             "account_free_quota_verified_by_this_probe": False}
            for key, counts in sorted(by_model.items())],
        "all_configured_models_covered": False,
    }


def heartbeat(state, *, now):
    """Read bounded fixed-name heartbeat; never dump arbitrary private JSON."""
    path = Path(state) / "continuous-status.json"
    answer = {"available": False, "recent": False}
    if path.is_symlink() or not path.is_file():
        return answer
    try:
        if path.stat().st_size > 65536:
            return answer
        item = json.loads(path.read_text())
        if not isinstance(item, dict):
            return answer
        observed = item.get("observed_at")
        if not valid_number(observed) or observed > now + 60:
            return answer
        delta = max(0, now - observed)
        info = item.get("dispatch")
        info = info if isinstance(info, dict) else {}
        return {
            "available": True,
            "recent": delta <= 1200,
            "age_seconds": int(delta),
            "last_tick_at": observed,
            "last_tick_executed_claim_or_job": (
                item.get("executed") if type(item.get("executed")) is int
                and 0 <= item.get("executed") <= 9 else None),
            "last_tick_review_ready_draft": item.get("review_ready") is True,
            "last_tick_feed": item.get("feed")
               if item.get("feed") in FEEDS else "unknown",
            "last_tick_dispatch_reason": info.get("reason")
               if info.get("reason") in REASONS else "unknown",
            "last_tick_queued": info.get("queued")
               if type(info.get("queued")) is int
               and 0 <= info.get("queued") <= 10000000 else None,
        }
    except (OSError, ValueError, UnicodeError):
        return answer


def inspect(state, *, now=None):
    now = time.time() if now is None else now
    if not valid_number(now):
        raise ValueError("invalid clock")
    with snapshot(state) as conn:
        data = collect(conn, now=now)
    data["heartbeat"] = heartbeat(state, now=now)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=(
        Path.home() / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"))
    args = parser.parse_args(argv)
    try:
        result = inspect(args.state)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, sqlite3.Error, TypeError):
        # Never echo path, arbitrary SQLite data or raw private provider errors.
        print(json.dumps({"status": "read_only_snapshot_unavailable",
                          "observation_only": True,
                          "inference_requests_sent_by_probe": 0,
                          "raw_private_content_exposed": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
