#!/usr/bin/env python3
"""Pacing decisions and read-only health for the existing OmniRoute worker.

This module does not claim jobs, call models, change quotas, or start services.
Use dispatch_decision inside the existing SQLite claim transaction to enforce
pacing; a separate preflight is advisory and cannot prevent concurrent claims.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import plistlib
import shutil
import sqlite3
import stat
import tempfile
import time

DAY = 86400
LABEL = "com.rovor.ghost-worker.readonly"


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def recommended_interval(max_claims):
    if type(max_claims) is not int or not 1 <= max_claims <= 10000:
        raise ValueError("invalid claim limit")
    # The existing claim query includes the lower window boundary (>=).
    return math.ceil(DAY / max_claims) + 1


def dispatch_decision(*, now, claims, max_claims, queued, running=0,
                      stopped=False, circuit_open=False, pace_seconds=0):
    """Return a sanitized admission decision, never permission to bypass guards.

    claims must come from the authoritative ledger and include every claimed
    attempt in the last 24 hours, including failures and manual canaries.
    now/ledger must be read while holding the existing claim transaction.
    """
    recommended = recommended_interval(max_claims)
    if (not _number(now) or now < 0 or not _number(pace_seconds)
            or pace_seconds < 0 or type(stopped) is not bool
            or type(circuit_open) is not bool
            or any(type(x) is not int or x < 0 for x in (queued, running))
            or not isinstance(claims, (list, tuple))):
        raise ValueError("invalid dispatch evidence")
    if any(not _number(t) or t < 0 or t > now for t in claims):
        raise ValueError("invalid claim timestamp")
    recent = sorted(t for t in claims if t >= now - DAY)
    quota_at = (math.floor(recent[-max_claims] + DAY) + 1
                if len(recent) >= max_claims else now)
    pace_at = recent[-1] + pace_seconds if recent else now
    next_at = max(now, quota_at, pace_at)
    result = {"allowed": False, "reason": None, "next_eligible_at": None,
              "claims_last_24h": len(recent), "max_claims_24h": max_claims,
              "queued": queued, "running": running,
              "pacing_seconds": pace_seconds,
              "recommended_pacing_seconds": recommended}
    if stopped:
        result["reason"] = "stop_requested"
    elif circuit_open:
        result["reason"] = "failure_circuit_requires_review"
    elif running:
        result["reason"] = "existing_work_running"
    elif not queued:
        result["reason"] = "no_queued_work"
    elif next_at > now:
        result.update(reason="rolling_quota" if quota_at > now else "paced_wait",
                      next_eligible_at=next_at)
    else:
        result.update(allowed=True, reason="eligible", next_eligible_at=now)
    return result


def _signature(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024 * 1024:
        raise ValueError("unsafe or oversized database file")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


@contextmanager
def snapshot(state):
    """Open only a stable local copy; SQLite never touches live WAL/SHM files."""
    state = Path(state)
    if state.is_symlink() or not state.is_dir():
        raise ValueError("invalid existing state directory")
    paths = [state / "jobs.sqlite3", state / "jobs.sqlite3-wal"]
    with tempfile.TemporaryDirectory(prefix="rovor-quota-") as folder:
        before = [_signature(p) if p.exists() or p.is_symlink() else None
                  for p in paths]
        if before[0] is None:
            raise ValueError("existing worker database missing")
        for path, signature in zip(paths, before):
            if signature is not None:
                shutil.copyfile(path, Path(folder) / path.name)
        after = [_signature(p) if p.exists() or p.is_symlink() else None
                 for p in paths]
        if before != after:
            raise ValueError("database changed during snapshot; retry later")
        conn = sqlite3.connect(str(Path(folder) / "jobs.sqlite3"))
        conn.row_factory = sqlite3.Row
        try:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("database snapshot invalid")
            yield conn
        finally:
            conn.close()


def read_health(plist_path, *, now=None):
    now = time.time() if now is None else now
    path = Path(plist_path)
    _signature(path)
    config = plistlib.loads(path.read_bytes())
    args = config.get("ProgramArguments")
    if (config.get("Label") != LABEL or not isinstance(args, list)
            or any(not isinstance(x, str) for x in args)
            or len(args) < 2 or Path(args[1]).name != "ghost_worker_loop.py"):
        raise ValueError("unexpected existing LaunchAgent")

    def value(flag):
        if args.count(flag) != 1 or args.index(flag) + 1 >= len(args):
            raise ValueError("missing or repeated worker option")
        return args[args.index(flag) + 1]

    state = Path(value("--state"))
    limit = int(value("--max-omniroute-claims-per-day"))
    marker = state / "STOP"
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise ValueError("invalid STOP marker")
    with snapshot(state) as conn:
        rows = conn.execute(
            "SELECT e.timestamp,j.status,j.result FROM events e "
            "JOIN jobs j ON j.id=e.job_id WHERE e.event='claimed' "
            "AND j.kind='research.omniroute' AND e.timestamp>=? "
            "ORDER BY e.timestamp DESC,e.id DESC", (now - DAY,)).fetchall()
        failures = 0
        for row in rows[:3]:
            outcome = json.loads(row["result"] or "{}")
            if not isinstance(outcome, dict):
                raise ValueError("unknown job outcome")
            if (row["status"] == "failed" or outcome.get("draft_status") ==
                    "needs_review_no_auto_retry"):
                failures += 1
            else:
                break
        counts = dict(conn.execute(
            "SELECT status,count(*) FROM jobs WHERE kind='research.omniroute' "
            "GROUP BY status").fetchall())
        decision = dispatch_decision(
            now=now, claims=[r["timestamp"] for r in rows], max_claims=limit,
            queued=counts.get("queued", 0), running=counts.get("running", 0),
            stopped=marker.exists(), circuit_open=failures >= 3)
    next_at = decision["next_eligible_at"]
    decision.update(
        observation_only=True, model_requests=0, state_modified=False,
        launchagent_loaded_verified=False,
        pacing_installed=False, consecutive_recorded_failures=failures,
        earliest_eligible_utc=(datetime.fromtimestamp(next_at, timezone.utc)
                               .isoformat() if next_at is not None else None),
        scheduled_interval_seconds=config.get("StartInterval"))
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launchagent", type=Path, default=(
        Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")))
    args = parser.parse_args()
    try:
        result = read_health(args.launchagent)
    except (OSError, ValueError, TypeError, sqlite3.Error, OverflowError):
        print(json.dumps({"reason": "health_evidence_unavailable",
                          "allowed": False, "model_requests": 0}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
