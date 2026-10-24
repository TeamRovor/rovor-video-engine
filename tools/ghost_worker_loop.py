#!/usr/bin/env python3
"""Bounded foreground poller for ROVOR's SQLite ghost worker.

This is not a daemon, AI model, login agent, shell executor, or publishing tool.
Only the adapters currently permitted by ghost_worker.py can execute.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import sqlite3
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
         sleeper=time.sleep, allow_model_use=False, allow_native_import=False,
         allow_jane_library_create=False, jane_queue_job_id=None,
         allow_omniroute_model_use=False, allow_omniroute_work_plan=False,
         parallel_omniroute_workers=1) -> dict:
    """Poll bounded jobs with explicit opt-ins, observing STOP between operations.

    Limits are cooperative: a synchronous adapter cannot be interrupted mid-call.
    The underlying SQLite claim transaction prevents duplicate claimed jobs.
    """
    validate_limits(max_jobs=max_jobs, max_seconds=max_seconds, poll_seconds=poll_seconds)
    if (type(parallel_omniroute_workers) is not int or not 1 <= parallel_omniroute_workers <= 3):
        raise ValueError('Parallel worker count must be 1 to 3')
    if parallel_omniroute_workers > 1 and (
            not allow_omniroute_work_plan or not allow_omniroute_model_use
            or allow_model_use or allow_native_import or allow_jane_library_create
            or jane_queue_job_id or max_jobs < parallel_omniroute_workers):
        raise ValueError('Parallel work requires separately approved OmniRoute-only research')
    if allow_omniroute_work_plan and (not allow_omniroute_model_use or allow_model_use
                                    or allow_native_import or allow_jane_library_create):
        raise ValueError('Work plan requires OmniRoute-only approval')
    if allow_jane_library_create and (not jane_queue_job_id or max_jobs != 1):
        raise ValueError('Jane native creation requires one exact queue job ID and max-jobs=1')
    if jane_queue_job_id and not allow_jane_library_create:
        raise ValueError('Jane native queue job ID needs explicit approval')
    if not isinstance(worker_id, str) or not (1 <= len(worker_id) <= 128):
        raise ValueError("A worker-id of 1 to 128 characters is required")
    # Resolve/check before executing any work. Never create a state directory here.
    _state_dir(state)
    start = monotonic()
    feed_result = None
    if allow_omniroute_work_plan:
        import ghost_omniroute_feed
        if parallel_omniroute_workers > 1:
            feed_result = ghost_omniroute_feed.feed_parallel(
                conn, state, Path(__file__).resolve().parent.parent,
                limit=parallel_omniroute_workers)
        else:
            feed_result = ghost_omniroute_feed.feed(
                conn, state, Path(__file__).resolve().parent.parent)
    if parallel_omniroute_workers > 1:
        # Each thread owns a connection. SQLite's BEGIN IMMEDIATE atomically
        # claims the job and enforces the existing five/24h model claim limit.
        state_db = _state_dir(state) / "jobs.sqlite3"
        def one(index):
            if stop_requested(state):
                return None
            with closing(sqlite3.connect(str(state_db), timeout=20,
                                         isolation_level=None)) as scoped:
                scoped.row_factory = sqlite3.Row
                scoped.execute("PRAGMA busy_timeout=20000")
                return ghost_worker.run_once(
                    scoped, workspace, owner=worker_id + "/specialist-" + str(index),
                    allow_omniroute_model_use=True)
        with ThreadPoolExecutor(max_workers=parallel_omniroute_workers) as pool:
            receipts = list(pool.map(one, range(parallel_omniroute_workers)))
        nonempty = [receipt for receipt in receipts if receipt is not None]
        return {"stop_reason": "parallel_tick_complete", "executed": len(nonempty),
                "succeeded": sum(x["status"] == "succeeded" for x in nonempty),
                "failed": sum(x["status"] == "failed" or
                              (x.get("result") or {}).get("draft_status") == "needs_review_no_auto_retry"
                              for x in nonempty),
                "review_ready": sum((x.get("result") or {}).get("draft_status")
                                    == "draft_completed_needs_review" and
                                    (x.get("result") or {}).get("review_status")
                                    == "draft_ready_for_human_review"
                                    for x in nonempty),
                "needs_review": sum(x["status"] == "needs_review" for x in nonempty),
                "work_plan": feed_result, "parallel_workers": parallel_omniroute_workers,
                "read_only": False, "native_import_enabled": False,
                "model_use_enabled": False, "omniroute_model_use_enabled": True,
                "worker_id": worker_id}
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
        if allow_jane_library_create:
            receipt = ghost_worker.run_once(
                conn, workspace, owner=worker_id,
                allow_model_use=allow_model_use,
                allow_native_import=allow_native_import,
                allow_jane_library_create=True,
                jane_library_only=True,
                jane_queue_job_id=jane_queue_job_id,
                allow_omniroute_model_use=allow_omniroute_model_use)
        elif allow_native_import:
            receipt = ghost_worker.run_once(conn, workspace, owner=worker_id,
                                           allow_model_use=allow_model_use, allow_native_import=True,
                                           allow_omniroute_model_use=allow_omniroute_model_use)
        elif allow_model_use or allow_omniroute_model_use:
            receipt = ghost_worker.run_once(conn, workspace, owner=worker_id,
                                           allow_model_use=allow_model_use,
                                           allow_omniroute_model_use=allow_omniroute_model_use)
        else:
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
            "work_plan": feed_result,
            "failed": failed, "idle_polls": idle_polls,
            "elapsed_seconds": round(max(0, monotonic() - start), 3),
            "read_only": not (allow_model_use or allow_omniroute_model_use or allow_jane_library_create),
            "native_import_requested": allow_native_import,
            "native_import_enabled": False,
            "jane_library_creation_approved": allow_jane_library_create,
            "native_timeline_verified": False,
            "model_use_enabled": allow_model_use,
            "omniroute_model_use_enabled": allow_omniroute_model_use,
            "worker_id": worker_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path, help="Private existing worker state directory")
    parser.add_argument("--workspace", required=True, type=Path, help="Explicitly authorized workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Poll jobs with hard count and cooperative time limits")
    run.add_argument("--worker-id", default="rovor-local-worker")
    run.add_argument("--approve-model-use", action="store_true")
    run.add_argument("--approve-omniroute-model-use", action="store_true",
                     help="Enable separately approved capped OmniRoute research jobs")
    run.add_argument("--parallel-omniroute-workers", type=int, default=1,
                     help="Opt-in one to three independent bounded OmniRoute research claims")
    run.add_argument("--approve-omniroute-work-plan", action="store_true",
                     help="Feed the finite released draft plan once; never replay completed jobs")
    run.add_argument("--allow-native-import", action="store_true")
    run.add_argument("--approve-jane-library-create", action="store_true",
                     help="One exact approved native library job; no XML import")
    run.add_argument("--jane-queue-job-id", help="Exact queued Jane UUID; requires --max-jobs=1")
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
                          poll_seconds=args.poll_seconds, allow_model_use=args.approve_model_use,
                          allow_native_import=args.allow_native_import,
                          allow_omniroute_model_use=args.approve_omniroute_model_use,
                          allow_omniroute_work_plan=args.approve_omniroute_work_plan,
                          parallel_omniroute_workers=args.parallel_omniroute_workers,
                          allow_jane_library_create=args.approve_jane_library_create,
                          jane_queue_job_id=args.jane_queue_job_id)
    elif args.command == "stop":
        result = {"stop_requested": True, "marker_created": request_stop(args.state)}
    else:
        result = {"stop_requested": False, "marker_removed": clear_stop(args.state)}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

