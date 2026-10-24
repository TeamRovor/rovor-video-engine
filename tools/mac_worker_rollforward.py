#!/usr/bin/env python3
"""Operator-only, rollback-capable upgrade of the EXISTING ROVOR Mac LaunchAgent.

No downloads, git writes, model requests, new scheduler, credential reads,
quota changes, secret output, native applications or automatic activation.
Requires an isolated reviewed checkout and the exact pinned 40-hex commit.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

LABEL = "com.rovor.ghost-worker.readonly"
PLIST = LABEL + ".plist"
REQUIRED_FLAGS = ("--approve-omniroute-model-use", "--approve-omniroute-work-plan")
SHA = re.compile(r"^[a-f0-9]{40}$")


class Blocked(ValueError):
    pass


def checked(path, *, directory=False, regular=False):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise Blocked("redirected_path")
    if directory and not path.is_dir():
        raise Blocked("directory_missing")
    if regular and not path.is_file():
        raise Blocked("file_missing")
    return path


def call(argv, run=subprocess.run, timeout=15):
    try:
        return run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Blocked("local_command_unavailable") from None


def local_candidate(checkout, expected, *, run=subprocess.run):
    if not SHA.fullmatch(expected):
        raise Blocked("expected_commit_invalid")
    checkout = checked(checkout, directory=True)
    if checkout.name != "worker-runtime-" + expected[:12]:
        raise Blocked("candidate_name_not_isolated")
    script = checked(checkout / "tools" / "ghost_worker_loop.py", regular=True)
    checked(checkout / "tools" / "omniroute_workpack_runner.py", regular=True)
    checked(checkout / "tools" / "ghost_omniroute_feed.py", regular=True)
    verified = call(["git", "-C", str(checkout), "rev-parse", "HEAD"], run)
    dirty = call(["git", "-C", str(checkout), "status", "--porcelain"], run)
    if verified.returncode or verified.stdout.strip() != expected:
        raise Blocked("candidate_commit_mismatch")
    if dirty.returncode or dirty.stdout.strip():
        raise Blocked("candidate_checkout_dirty")
    return script


def state_snapshot(state):
    """Examine a copy, never open/change the live WAL database."""
    state = checked(state, directory=True)
    if stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise Blocked("state_not_private")
    if checked(state / "STOP").exists():
        raise Blocked("owner_stop_present")
    for side in ("jobs.sqlite3-wal", "jobs.sqlite3-shm"):
        if (state / side).is_symlink():
            raise Blocked("database_sidecar_redirected")
        if (state / side).exists():
            raise Blocked("database_has_live_sidecar")
    db = checked(state / "jobs.sqlite3", regular=True)
    before = db.stat()
    with tempfile.TemporaryDirectory(prefix="rovor-upgrade-check-") as folder:
        snap = Path(folder) / "jobs.sqlite3"
        shutil.copyfile(db, snap)
        after = db.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise Blocked("database_changed_during_snapshot")
        try:
            conn = sqlite3.connect(str(snap), timeout=5)
            try:
                if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise Blocked("sqlite_integrity_failed")
                running = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
                if running:
                    raise Blocked("active_jobs_present")
            finally:
                conn.close()
        except sqlite3.Error:
            raise Blocked("database_snapshot_unreadable") from None
    return True


def inspect(home, checkout, expected, *, run=subprocess.run, platform=sys.platform, uid=os.getuid,
            approve_parallel=False):
    if platform != "darwin":
        raise Blocked("mac_gui_session_required")
    home = checked(home, directory=True)
    base = checked(home / "Documents" / "Rovor", directory=True)
    checkout = checked(checkout, directory=True)
    if checkout.parent != base:
        raise Blocked("candidate_outside_isolated_mac_root")
    script = local_candidate(checkout, expected, run=run)
    plist = checked(home / "Library" / "LaunchAgents" / PLIST, regular=True)
    try:
        current = plistlib.loads(plist.read_bytes())
    except (ValueError, TypeError, OSError, plistlib.InvalidFileException):
        raise Blocked("existing_plist_unreadable") from None
    if (current.get("Label") != LABEL or current.get("RunAtLoad") is not True
            or current.get("StartInterval") != 300
            or current.get("KeepAlive") is not False):
        raise Blocked("unexpected_existing_schedule")
    args = current.get("ProgramArguments")
    if not isinstance(args, list) or len(args) < 8 or not all(isinstance(x, str) for x in args):
        raise Blocked("unexpected_existing_program_arguments")
    python = Path(args[0])
    if not python.is_file() or not os.access(python, os.X_OK):
        raise Blocked("original_python_unavailable")
    oldscript = checked(args[1], regular=True)
    if oldscript.resolve() == script.resolve() or oldscript.name != "ghost_worker_loop.py":
        raise Blocked("source_runtime_not_distinct")
    if oldscript.parent.name != "tools":
        raise Blocked("old_runtime_layout_unexpected")
    if args.count("--state") != 1 or args.count("--workspace") != 1 or args.count("run") != 1:
        raise Blocked("program_arguments_not_unique")
    if any(args.count(flag) != 1 for flag in REQUIRED_FLAGS):
        raise Blocked("model_and_feed_approval_not_preserved")
    state = checked(Path(args[args.index("--state") + 1]), directory=True)
    workspace = checked(Path(args[args.index("--workspace") + 1]), directory=True)
    if state != home / "Documents" / "Codex" / "2026-10-22" / "new-chat" / "jane-worker-state":
        raise Blocked("noncanonical_state")
    if workspace != base:
        raise Blocked("noncanonical_workspace")
    state_snapshot(state)
    domain = "gui/" + str(uid())
    seen = call(["/bin/launchctl", "print", domain + "/" + LABEL], run)
    if seen.returncode:
        raise Blocked("existing_launchagent_not_verified")
    revised = dict(current)
    revised["ProgramArguments"] = list(args)
    revised["ProgramArguments"][1] = str(script)
    if approve_parallel:
        if "--max-jobs" not in args or args.count("--max-jobs") != 1:
            raise Blocked("parallel_job_limit_not_explicit")
        index = args.index("--max-jobs") + 1
        if index >= len(args) or args[index] != "1":
            raise Blocked("parallel_old_job_limit_unexpected")
        revised["ProgramArguments"][index] = "3"
        revised["ProgramArguments"].extend(["--parallel-omniroute-workers", "3"])
    return {"plist": plist, "state": state, "domain": domain,
            "original": current, "replacement": revised, "oldscript": oldscript,
            "candidate_python": python, "candidate": checkout}


def atomic_plist(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".rovor-atomic-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            plistlib.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def rollforward(info, *, run=subprocess.run):
    """Stop -> swap one program path -> bootstrap -> verify; rollback on error."""
    marker = info["state"] / "STOP"
    if os.path.lexists(marker):
        raise Blocked("owner_stop_present")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        raise Blocked("owner_stop_present") from None
    with os.fdopen(fd, "w") as output:
        output.write("ROVOR reviewed runtime rollforward; do not delete during rollout.\n")
    old = info["original"]
    path = info["plist"]
    domain = info["domain"]
    target = domain + "/" + LABEL
    backup = path.with_name(path.name + ".pre-rollforward")
    switched = False
    old_unloaded = False
    try:
        if backup.exists() or backup.is_symlink():
            raise Blocked("existing_backup_requires_review")
        with open(backup, "xb") as output:
            output.write(plistlib.dumps(old))
        os.chmod(backup, 0o600)
        stop = call(["/bin/launchctl", "bootout", target], run)
        if stop.returncode:
            raise Blocked("could_not_pause_existing_service")
        old_unloaded = True
        atomic_plist(path, info["replacement"])
        switched = True
        start = call(["/bin/launchctl", "bootstrap", domain, str(path)], run)
        seen = call(["/bin/launchctl", "print", target], run)
        if start.returncode or seen.returncode:
            raise Blocked("candidate_launch_not_verified")
        marker.unlink()
        return {"status": "new_candidate_loaded_existing_label",
                "unattended_model_execution_verified": False,
                "queued_job_execution_verified": False,
                "next_live_receipt_required": True}
    except Exception:
        # Emergency STOP stays present after failure. Do not resume jobs.
        if switched:
            call(["/bin/launchctl", "bootout", target], run)
            atomic_plist(path, old)
        if old_unloaded:
            call(["/bin/launchctl", "bootstrap", domain, str(path)], run)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--approve-rollforward", action="store_true")
    parser.add_argument("--approve-parallel-free-research", action="store_true",
                        help="Up to three concurrent preapproved research jobs; same free-only daily cap")
    args = parser.parse_args(argv)
    try:
        info = inspect(Path.home(), args.candidate, args.expected_commit,
                       approve_parallel=args.approve_parallel_free_research)
        if not args.approve_rollforward:
            result = {"status": "read_only_candidate_ready",
                      "state_integrity_verified": True, "old_service_loaded": True,
                      "commit_verified": True, "source_changed": False,
                      "model_calls": 0, "activation_performed": False}
        else:
            result = rollforward(info)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Blocked, OSError, ValueError) as exc:
        code = str(exc) if isinstance(exc, Blocked) else "local_upgrade_unavailable"
        print(json.dumps({"status": "blocked", "reason": code,
                          "model_calls": 0, "activation_confirmed": False}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
