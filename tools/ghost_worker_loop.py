#!/usr/bin/env python3
"""Bounded, foreground poller for ROVOR's read-only SQLite ghost worker.

This is not a daemon, AI model, login agent, shell executor, or publishing tool.
Only the adapters currently permitted by ghost_worker.py can execute.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import time

import ghost_worker

MAX_RUN_SECONDS = 3600
MAX_RUN_JOBS = 1000
MIN_POLL_SECONDS = 0.1
MAX_POLL_SECONDS = 30.0
STOP_BASENAME = "STOP"


def validate_limits(*, max_jobs: int, max_seconds: float, poll_seconds: float) -> None:
    """Guard foreground execution before opening the job database."""
    if type(max_jobs) is not int or not 1 <= max_jobs <= MAX_RUN_JOBS:
        raise ValueError(f"max-jobs must be an integer between 1 and {MAX_RUN_JOBS}")
    if type(max_seconds) not in (int, float) or not 0 < max_seconds <= MAX_RUN_SECONDS:
        raise ValueError(f"max-seconds must be between 0 (exclusive) and {MAX_RUN_SECONDS}")
    if type(poll_seconds) not in (int, float) or not MIN_POLL_SECONDS <= poll_seconds <= MAX_POLL_SECONDS:
        raise ValueError(f"poll-seconds must be between {MIN_POLL_SECONDS} and {MAX_POLL_SECONDS}")


def _state_dir(state: Path) -> Path:
    p = Path(state).expanduser()
    if p.is_symlink():
        raise ValueError("Worker state directory must not be a symlink")
    resolved = p.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("Worker state must be an initialized directory")
    return resolved


def _stop_path(state: Path) -> Path:
    return _state_dir(state) / STOP_BASENAME


def stop_requested(state: Path) -> bool:
    target = _stop_path(state)
    if target.is_symlink():
        raise ValueError("STOP marker must not be a symlink")
    if target.exists() and not target.is_file():
        raise ValueError("STOP marker must be an ordinary file")
    return target.exists()


def request_stop(state: Path) -> bool:
    """Create a persistent stop marker. Safe to request repeatedly."""
    marker = _stop_path(state)
    if stop_requested(state):
        return False
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        if not stop_requested(state):
            raise ValueError("STOP marker race or invalid marker")
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("ROVOR worker stop requested; use resume to clear.\n")
    return True


def clear_stop(state: Path) -> bool:
    """Clear the marker for a *future* foreground run; never starts a process."""
    marker = _stop_path(state)
    if not stop_requested(state):
        return False
    marker.unlink()
    return True


def poll(conn, workspace: Path, state: Path, *, worker_id: str,
         max_jobs: int = 100, max_seconds: float = 900,
         poll_seconds: float = 1.0, monotonic=time.monotonic,
         sleeper=time.sleep) -> dict:
    """Poll bounded read-only jobs, observing STOP between operations.

    Limits are cooperative: a synchronous adapter cannot be interrupted mid-call.
    The underlying SQLite claim transaction prevents duplicate claimed jobs.
    """
    validate_limits(max_jobs=max_jobs, max_seconds=max_seconds, poll_seconds=poll_seconds)
    if not isinstance(worker_id, str) or not (1 <= len(worker_id) <= 128):
        raise ValueError("A worker-id of 1 to 128 characters is required")
    # Resolve/check before executing any work. Never create a state directory here.
    _state_dir(state)
    start = monotonic()
    executed = succeeded = failed = idle_polls = 0
    while True:
        if stop_requested(state):
            reason = "stop_requested"
            break
        if executed >= max_jobs:
            reason = "max_jobs"
            break
        elapsed = max(0, monotonic() - start)
        if elapsed >= max_seconds:
            reason = "max_seconds"
            break
        receipt = ghost_worker.run_once(conn, workspace, owner=worker_id)
        if receipt is not None:
            executed += 1
            if receipt["status"] == "succeeded":
                succeeded += 1
            else:
                failed += 1
            continue
        idle_polls += 1
        remaining = max_seconds - max(0, monotonic() - start)
        if remaining > 0:
            sleeper(min(poll_seconds, remaining))
    return {"stop_reason": reason, "executed": executed, "succeeded": succeeded,
            "failed": failed, "idle_polls": idle_polls,
            "elapsed_seconds": round(max(0, monotonic() - start), 3),
            "read_only": True, "worker_id": worker_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path, help="Private existing worker state directory")
    parser.add_argument("--workspace", required=True, type=Path, help="Explicitly authorized workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Poll read-only jobs in foreground with hard count and cooperative time limits")
    run.add_argument("--worker-id", default="rovor-local-worker")
    run.add_argument("--max-jobs", type=int, default=100)
    run.add_argument("--max-seconds", type=float, default=900)
    run.add_argument("--poll-seconds", type=float, default=1.0)
    sub.add_parser("stop", help="Persist a STOP marker; running poller stops between jobs")
    sub.add_parser("resume", help="Remove STOP marker; does not start the poller")
    args = parser.parse_args()
    if args.command == "run":
        validate_limits(max_jobs=args.max_jobs, max_seconds=args.max_seconds, poll_seconds=args.poll_seconds)
        with closing(ghost_worker.connect(args.state)) as conn:
            result = poll(conn, args.workspace, args.state, worker_id=args.worker_id,
                          max_jobs=args.max_jobs, max_seconds=args.max_seconds,
                          poll_seconds=args.poll_seconds)
    elif args.command == "stop":
        result = {"stop_requested": True, "marker_created": request_stop(args.state)}
    else:
        result = {"stop_requested": False, "marker_removed": clear_stop(args.state)}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
