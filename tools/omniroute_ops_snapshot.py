#!/usr/bin/env python3
"""One read-only local ROVOR operations snapshot: real jobs + routed models + quota.

Designed to run directly from a pinned Git object using "git show ... | python3 -".
No installed source import, API key, gateway completion, queue write or LaunchAgent
change is needed. Never print raw provider JSON, private drafts, paths or errors.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

MODEL = re.compile(r"^[a-z0-9][a-z0-9._:/-]{2,159}$")
COMBO = re.compile(r"^rovor-[a-z0-9-]{3,90}$")
PROVIDERS = ("cohere", "gemini", "groq", "mistral", "nvidia", "openrouter")
TICK_FEED = frozenset((
    "existing_queue", "new_public_task_assignment_queued",
    "distinct_assignment_queued", "catalogue_exhausted_new_work_required",
    "stop_requested"))
TICK_REASONS = frozenset((
    "stop_requested", "failure_circuit_requires_review", "existing_work_running",
    "no_queued_work", "rolling_quota", "paced_wait", "eligible",
    "quota_exhausted"))
VERSION = re.compile(r"(?<![\d.])(\d{1,3}\.\d{1,3}\.\d{1,4})(?![\d.])")


def _json_result(argv, *, run=subprocess.run, timeout=8):
    """Trust none of the CLI output; NEVER forward unstructured stdout/stderr."""
    try:
        cp = run(argv, input=b"", capture_output=True, timeout=timeout,
                 check=False)
        raw = cp.stdout
        if cp.returncode or type(raw) is not bytes or len(raw) > 524288:
            return None
        text = raw.decode("utf-8")
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char in "[{":
                try:
                    value, _ = decoder.raw_decode(text, index)
                except ValueError:
                    continue
                if isinstance(value, (dict, list)):
                    return value
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError):
        pass
    return None


def _cli_version(path, *, run=subprocess.run):
    try:
        cp = run([path, "--version"], input=b"", capture_output=True,
                 timeout=5, check=False)
        if cp.returncode or type(cp.stdout) is not bytes or len(cp.stdout) > 4096:
            return None
        match = VERSION.search(cp.stdout.decode("utf-8"))
        return match.group(1) if match else None
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return None


def _connections(doc):
    rows = doc if isinstance(doc, list) else None
    if isinstance(doc, dict):
        rows = next((doc[x] for x in ("connections", "providers", "items", "data")
                     if isinstance(doc.get(x), list)), None)
        if rows is None and isinstance(doc.get("data"), dict):
            inner = doc["data"]
            rows = next((inner[x] for x in ("connections", "providers", "items")
                         if isinstance(inner.get(x), list)), None)
    if not isinstance(rows, list) or len(rows) > 200 or any(
            not isinstance(x, dict) for x in rows):
        return None
    counts = Counter()
    for row in rows:
        # Only known provider *types* are published. Provider IDs, login names,
        # account labels and stored credentials are NEVER copied to the report.
        raw = row.get("type") or row.get("provider") or row.get("kind")
        counts[raw if type(raw) is str and raw in PROVIDERS else "other"] += 1
    return {"entries": len(rows), "provider_type_counts": dict(sorted(counts.items()))}


def _routes(doc):
    rows = doc.get("combos") if isinstance(doc, dict) else None
    if not isinstance(rows, list) or len(rows) > 200:
        return None
    combos = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        name = row.get("name")
        if type(name) is not str or not name.startswith("rovor-"):
            continue
        if not COMBO.fullmatch(name) or name in combos:
            return None
        entries = row.get("models")
        if (not isinstance(entries, list) or
                not 1 <= len(entries) <= 20):
            return None
        ids = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("kind") != "model":
                return None
            ident = entry.get("model")
            if type(ident) is not str or not MODEL.fullmatch(ident):
                return None
            ids.append(ident)
        combos[name] = {"model_ids": ids, "single_model": len(ids) == 1,
                        "free_suffix_only": all(x.endswith(":free") for x in ids)}
    models = sorted({model for combo in combos.values() for model in combo["model_ids"]})
    return {
        "rovor_combo_count": len(combos),
        "distinct_routed_models": len(models),
        "routed_model_ids": models,
        "worker_role_route_mapping_verified_by_this_probe": False,
        "combos": dict(sorted(combos.items())),
        "working_model_completions_verified": False,
        "free_account_billing_verified": False,
    }


def _catalogue(doc, route_ids):
    # Model list is merely advertised metadata, not a successful inference or
    # proof of zero cost. Do not echo vendor descriptions or user metadata.
    rows = doc if isinstance(doc, list) else None
    if isinstance(doc, dict):
        rows = next((doc[x] for x in ("models", "items", "data")
                     if isinstance(doc.get(x), list)), None)
        if rows is None and isinstance(doc.get("data"), dict):
            inner = doc["data"]
            rows = next((inner[x] for x in ("models", "items")
                         if isinstance(inner.get(x), list)), None)
    if not isinstance(rows, list) or len(rows) > 10000:
        return {"status": "unavailable_or_unknown_shape"}
    ids = set()
    for row in rows:
        if isinstance(row, str):
            ident = row
        elif isinstance(row, dict):
            ident = row.get("id") or row.get("model") or row.get("modelId")
        else:
            continue
        if type(ident) is str and MODEL.fullmatch(ident):
            ids.add(ident)
    return {
        "status": "catalogue_readable",
        "catalogue_distinct_model_ids": len(ids),
        "routed_ids_present_in_catalogue": sorted(ids.intersection(route_ids)),
        "catalogue_proves_model_works": False,
        "catalogue_proves_zero_cost": False,
    }


def _group(status, result):
    if status in ("queued", "running"):
        return status
    if type(result) is not str or len(result) > 65536:
        data = {}
    else:
        try:
            data = json.loads(result)
        except (ValueError, TypeError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    if status == "failed" or data.get("draft_status") == "needs_review_no_auto_retry":
        return "model_attempt_not_review_ready"
    if (status == "needs_review" and
            data.get("draft_status") == "draft_completed_needs_review" and
            data.get("review_status") == "draft_ready_for_human_review"):
        return "draft_ready_for_human_review"
    if status == "needs_review":
        return "pending_or_failed_review"
    return "unverified_other"


def _sqlite_snapshot(state, *, now):
    state = Path(state).expanduser()
    db = state / "jobs.sqlite3"
    if (state.is_symlink() or not state.is_dir()
            or db.is_symlink() or not db.is_file()):
        return {"status": "snapshot_unavailable"}
    for suffix in ("-wal", "-shm"):
        side = state / ("jobs.sqlite3" + suffix)
        if side.is_symlink() or (side.exists() and not side.is_file()):
            return {"status": "snapshot_unavailable"}
    # Consistent online backup: no SELECTs against an active writer's
    # transaction, no copying SQLite WAL+main independently, and no DB writes.
    dest = sqlite3.connect(":memory:")
    try:
        uri = db.absolute().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=4) as source:
            source.execute("PRAGMA query_only=ON")
            source.backup(dest, pages=128, sleep=0.05)
        rows = dest.execute(
            "SELECT id,status,result FROM jobs WHERE kind='research.omniroute'"
        ).fetchall()
        claims = dest.execute(
            "SELECT e.job_id,e.timestamp FROM events e "
            "JOIN jobs j ON e.job_id=j.id "
            "WHERE j.kind='research.omniroute' AND e.event='claimed' "
            "AND e.timestamp>=? AND e.timestamp<=?",
            (now - 86400, now)).fetchall()
        categories = {job: _group(status, result) for job, status, result in rows}
        totals = Counter(categories.values())
        distinct = {row[0] for row in claims}
        recent = Counter(categories.get(job, "unknown") for job in distinct)
        has_reservations = bool(dest.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='omni_model_reservations'").fetchone())
        model_count = dest.execute(
            "SELECT COUNT(*) FROM omni_model_reservations").fetchone()[0] if has_reservations else 0
        return {
            "status": "consistent_read_only_snapshot",
            "claims_last_24h": len(claims),
            "distinct_claimed_jobs_last_24h": len(distinct),
            "last_claim_at": max((t for _, t in claims), default=None),
            "outcomes_total": dict(sorted(totals.items())),
            "recent_claim_outcomes": dict(sorted(recent.items())),
            "review_ready_drafts_total": totals["draft_ready_for_human_review"],
            "human_accepted_deliverables_verified": False,
            "model_reservations_present": has_reservations,
            "model_reservations_total": model_count,
            "all_nine_models_used_verified": False,
        }
    except (sqlite3.Error, OSError, UnicodeError, ValueError):
        return {"status": "snapshot_unavailable"}
    finally:
        dest.close()


def _heartbeat(state, *, now):
    path = Path(state).expanduser() / "continuous-status.json"
    if path.is_symlink() or not path.is_file():
        return {"available": False}
    try:
        if path.stat().st_size > 65536:
            return {"available": False}
        item = json.loads(path.read_text())
        if not isinstance(item, dict):
            return {"available": False}
        observed = item.get("observed_at")
        if type(observed) not in (int, float) or not 0 <= observed <= now + 60:
            return {"available": False}
        dispatch = item.get("dispatch")
        dispatch = dispatch if isinstance(dispatch, dict) else {}
        age = max(0, int(now - observed))
        return {
            "available": True,
            "recent": age <= 1200,
            "age_seconds": age,
            "last_tick_executed": item.get("executed") if type(item.get("executed")) is int
                and item["executed"] in (0, 1) else None,
            "last_tick_feed": item.get("feed") if item.get("feed") in TICK_FEED else "unknown",
            "last_tick_dispatch": dispatch.get("reason")
                if dispatch.get("reason") in TICK_REASONS else "unknown",
        }
    except (OSError, ValueError, UnicodeError):
        return {"available": False}


def inspect(state, cli, *, now=None, run=subprocess.run):
    now = time.time() if now is None else now
    if type(now) not in (int, float) or not 0 <= now < 1e15:
        raise ValueError("invalid_clock")
    worker = _sqlite_snapshot(state, now=now)
    worker["heartbeat"] = _heartbeat(state, now=now)
    provider_doc = _json_result([cli, "providers", "list", "--json"], run=run)
    combo_doc = _json_result([cli, "combo", "list", "--json"], run=run)
    model_doc = _json_result([cli, "models", "--json"], run=run)
    quota_doc = _json_result([cli, "quota", "status", "--json"], run=run)
    # Some OmniRoute versions have a JSON flag on the parent quota command
    # but not status; only a read-only fallback is permitted.
    if quota_doc is None:
        quota_doc = _json_result([cli, "quota", "--json"], run=run)
    fleet = _routes(combo_doc)
    providers = _connections(provider_doc)
    if fleet is None:
        fleet = {"status": "route_inventory_unavailable",
                 "distinct_routed_models": None, "routed_model_ids": []}
    else:
        fleet["status"] = "route_inventory_readable"
    if providers is None:
        providers = {"status": "provider_inventory_unavailable"}
    else:
        providers["status"] = "provider_inventory_readable"
    catalogue = _catalogue(model_doc, fleet["routed_model_ids"])
    quota = {
        "status": "readable_unverified_content" if isinstance(quota_doc, dict)
            else "unavailable_or_unexpected_shape",
        # Parsing or quota data presence is never proof of billing terms.
        "zero_cost_entitlement_verified": False,
        "fresh_per_model_limits_verified": False,
        "ready_for_auto_fallback": False,
    }
    claimed = worker.get("claims_last_24h", 0)
    ready = worker.get("recent_claim_outcomes", {}).get("draft_ready_for_human_review", 0)
    ready_pct = round(ready * 100 / claimed) if claimed else None
    routed = fleet["distinct_routed_models"]
    if worker.get("status") != "consistent_read_only_snapshot":
        priority = "restore_read_only_worker_visibility"
    elif claimed and (ready_pct is None or ready_pct < 60):
        priority = "improve_draft_readiness_before_increasing_claim_rate"
    elif routed is None:
        priority = "restore_read_only_route_inventory"
    elif routed < 9:
        priority = "verify_additional_model_eligibility_before_routing"
    else:
        priority = "verify_model_accounts_and_successful_responses"
    return {
        "schema_version": 1,
        "kind": "rovor_single_command_workforce_snapshot",
        "observation_only": True,
        "gateway_completion_requests": 0,
        "service_or_queue_modified": False,
        "private_prompt_or_credentials_exposed": False,
        "observed_at": now,
        "cli_version": _cli_version(cli, run=run),
        "worker": worker,
        "providers": providers,
        "fleet": fleet,
        "model_catalogue": catalogue,
        "quota": quota,
        "recent_review_ready_rate_percent": ready_pct,
        "priority": priority,
        "next_safe_step": (
            "Improve task sizing and review failure categories; keep existing worker pacing"
            if priority == "improve_draft_readiness_before_increasing_claim_rate"
            else "Verify model/account free eligibility and real quota; keep the installed worker unchanged"),
        "target_models": 9,
        "nine_verified_active_models": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(
        Path.home() / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"))
    parser.add_argument("--omni", default=str(Path.home() / ".local/bin/omniroute"))
    args = parser.parse_args(argv)
    try:
        report = inspect(args.state, args.omni)
    except (OSError, ValueError, TypeError):
        report = {"status": "read_only_probe_unavailable", "observation_only": True,
                  "gateway_completion_requests": 0, "service_or_queue_modified": False,
                  "private_prompt_or_credentials_exposed": False}
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
