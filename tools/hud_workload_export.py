#!/usr/bin/env python3
"""Prepare a privacy-limited OFFLINE workload snapshot from reviewed Mac reports.

This is not a live connection, not a scheduler, and not proof of worker/model activity.
It never calls models, reads credentials, or infers missing metrics as zero.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{1,159}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")
EMPLOYEES = ("walter", "mike", "jane", "jesse", "gale", "gus", "saul", "hank")
WINDOWS = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}


class SnapshotError(ValueError):
    """Stable validation error, never includes private event data."""


def reject(code):
    raise SnapshotError(code)


def parse_utc(value):
    if not isinstance(value, str) or len(value) > 40:
        reject("timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        reject("timestamp_invalid")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta():
        reject("timestamp_must_be_utc")
    return parsed.astimezone(timezone.utc)


def stamp(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_snapshot(fleet, receipts=None, *, now=None):
    """Reduce an approved sanitized inventory and optional settled inference receipts.

    Receipts in a supplied file are NOT independently authenticated or complete.
    Therefore this tool never returns a 'verified_live' source or quota assertion.
    """
    observed = datetime.now(timezone.utc) if now is None else now
    if not isinstance(observed, datetime) or observed.tzinfo is None:
        reject("clock_invalid")
    observed = observed.astimezone(timezone.utc)
    if not isinstance(fleet, dict) or fleet.get("kind") != "omniroute_actual_model_coverage":
        reject("fleet_report_invalid")
    models = fleet.get("routed_model_ids")
    expected = fleet.get("nine_model_target")
    if (not isinstance(models, list) or len(models) > 64
            or not isinstance(expected, int) or isinstance(expected, bool)
            or not 1 <= expected <= 64):
        reject("fleet_model_count_invalid")
    if any(not isinstance(m, str) or not MODEL_RE.fullmatch(m) for m in models):
        reject("fleet_model_id_invalid")
    if len(set(models)) != len(models):
        reject("fleet_model_duplicate")
    # A provider connection is NOT a model or an accepted inference receipt.
    result = {
        "schema_version": 1,
        "source": "unattested_local_export",
        "verified_live": False,
        "snapshot_at": stamp(observed),
        "inventory": {
            "state": "configured_not_inference_verified",
            "expected_models": expected,
            "actual_models": len(models),
            "model_ids": sorted(models),
            "missing_from_expected": max(0, expected - len(models)),
        },
        "usage": {
            "state": "unknown" if receipts is None else "unattested_receipt_counts",
            "coverage": "unknown",
            "quota_remaining": None,
            "cost_usd": None,
            "windows": {name: None for name in WINDOWS},
        },
        "employees": list(EMPLOYEES),
    }
    if receipts is None:
        return result
    if isinstance(receipts, dict):
        receipts = receipts.get("receipts")
    if not isinstance(receipts, list) or len(receipts) > 10000:
        reject("receipts_shape_invalid")
    ids = set()
    parsed = []
    known = set(models)
    for r in receipts:
        if not isinstance(r, dict):
            reject("receipt_invalid")
        receipt_id, role, model, outcome = (
            r.get("receipt_id"), r.get("employee"), r.get("model_id"), r.get("outcome"))
        if not isinstance(receipt_id, str) or not ID_RE.fullmatch(receipt_id):
            reject("receipt_id_invalid")
        if receipt_id in ids:
            reject("receipt_duplicate")
        ids.add(receipt_id)
        if role not in EMPLOYEES or not isinstance(model, str) or model not in known:
            reject("receipt_unknown_route")
        if outcome not in ("completed", "failed"):
            reject("receipt_outcome_invalid")
        when = parse_utc(r.get("timestamp"))
        if when > observed + timedelta(minutes=1):
            reject("receipt_future_timestamp")
        parsed.append((when, role, model, outcome))
    for label, length in WINDOWS.items():
        start = observed - length
        accepted = [p for p in parsed if start <= p[0] <= observed]
        model_counts = {m: 0 for m in models}
        employee_matrix = {role: {m: 0 for m in models} for role in EMPLOYEES}
        completed = failed = 0
        for _, role, model, outcome in accepted:
            model_counts[model] += 1
            employee_matrix[role][model] += 1
            if outcome == "completed":
                completed += 1
            else:
                failed += 1
        result["usage"]["windows"][label] = {
            "from": stamp(start),
            "until": stamp(observed),
            "request_count": len(accepted),
            "completed_count": completed,
            "failed_count": failed,
            "model_counts": model_counts,
            "employee_model_counts": employee_matrix,
        }
    return result


def read_json(path):
    location = Path(path)
    try:
        if location.stat().st_size > 2_000_000:
            reject("input_oversized")
        with location.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        reject("input_unreadable")


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--fleet-report", required=True)
    cli.add_argument("--receipt-report", help="Optional reviewed/redacted inference receipt list")
    args = cli.parse_args(argv)
    try:
        report = build_snapshot(read_json(args.fleet_report),
                                read_json(args.receipt_report) if args.receipt_report else None)
    except SnapshotError as exc:
        print(json.dumps({"status": str(exc), "verified_live": False}))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
