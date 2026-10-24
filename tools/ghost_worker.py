#!/usr/bin/env python3
"""ROVOR durable job executor with read-only defaults and opt-in native import.

This job database records *execution jobs*, not GitHub development task ownership.
Legacy Final Cut import jobs require review; native dispatch is disabled.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
import sqlite3
import sys
import time
import uuid

ALLOWED = frozenset({"system.ping", "system.omniroute-preflight", "files.inventory"})
FUTURE_DISABLED = frozenset({
    "blender.scene", "moho.animate", "finalcut.timeline", "email.read",
    "email.send", "social.publish", "files.move", "files.delete",
})
RESEARCH_KIND = "research.finalcut"
OMNI_KIND = "research.omniroute"
TERMINAL_KIND = "terminal.probe"
OMNI_MAX_24H = 5
NATIVE_KIND = "finalcut.import-diagnostic"
LIBRARY_KIND = "finalcut.library-create"
NATIVE_DISABLED_REASON = (
    'Legacy native import disabled after wrong-library host evidence; '
    'verify isolated library creation and app selection before a replacement adapter')
MAX_PAYLOAD_BYTES = 4096
MAX_FILES = 2000
MAX_DEPTH = 6
LEASE_SECONDS = 120
MAX_ATTEMPTS = 2


def connect(state: Path) -> sqlite3.Connection:
    """Initialize one state database. Run from a trusted local user account."""
    raw_state = Path(state).expanduser()
    if raw_state.is_symlink():
        raise ValueError("state directory may not be a symlink")
    state = raw_state.resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = state / "jobs.sqlite3"
    # SQLite opens its sidecars too; reject redirected evidence before any open.
    for name in ("jobs.sqlite3", "jobs.sqlite3-wal", "jobs.sqlite3-shm"):
        path = state / name
        if path.is_symlink():
            raise ValueError("worker database paths may not be symlinks")
        if path.exists() and not path.is_file():
            raise ValueError("worker database paths must be regular files")
    conn = sqlite3.connect(str(db), timeout=20, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        payload TEXT NOT NULL,
        dedupe_key TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        lease_owner TEXT,
        lease_until REAL,
        result TEXT,
        error TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        event TEXT NOT NULL,
        detail TEXT NOT NULL,
        timestamp REAL NOT NULL
    );
    """)
    if db.exists():
        try:
            db.chmod(0o600)
        except OSError:
            pass
    return conn


def _event(conn: sqlite3.Connection, job_id: str, name: str, details: dict, now: float):
    conn.execute("INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)",
                 (job_id, name, json.dumps(details, sort_keys=True), now))


def enqueue(conn: sqlite3.Connection, kind: str, payload: dict,
            dedupe_key: str, now: float | None = None) -> str:
    if kind not in ALLOWED | {RESEARCH_KIND, OMNI_KIND, NATIVE_KIND, LIBRARY_KIND, TERMINAL_KIND}:
        raise ValueError(f"Adapter disabled or unknown: {kind}")
    if not isinstance(payload, dict) or not isinstance(dedupe_key, str) or not (1 <= len(dedupe_key) <= 200):
        raise ValueError("A JSON-object payload and nonempty dedupe key (max 200) are required")
    if kind == OMNI_KIND:
        import ghost_omniroute_job
        ghost_omniroute_job.validate_payload(payload)
    if kind in {"system.ping", "system.omniroute-preflight", RESEARCH_KIND, TERMINAL_KIND} and payload:
        raise ValueError("This fixed job does not accept parameters")
    if kind == LIBRARY_KIND:
        # Only stable slug; no arbitrary app commands, target paths or XML.
        import fcp_jane_library_onepass as jane
        if (set(payload) != {'job_id'}
                or not isinstance(payload['job_id'], str)
                or not jane.JOB_ID.fullmatch(payload['job_id'])):
            raise ValueError('Library-create payload requires one bounded job_id')
    if kind == NATIVE_KIND:
        if set(payload) != {'candidates'} or not isinstance(payload['candidates'], str):
            raise ValueError('Native diagnostic requires only a relative candidates directory')
        _relative_path(payload['candidates'])
    if kind == "files.inventory" and set(payload) - {"subpath"}:
        raise ValueError("Unsupported inventory payload parameter")
    if kind == "files.inventory" and not isinstance(payload.get("subpath", "."), str):
        raise ValueError("subpath must be a string")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("Payload too large")
    now = time.time() if now is None else now
    conn.execute("BEGIN IMMEDIATE")
    try:
        old = conn.execute("SELECT id,kind,payload FROM jobs WHERE dedupe_key=?", (dedupe_key,)).fetchone()
        if old:
            if old["kind"] != kind or old["payload"] != raw:
                raise ValueError("Dedupe key already assigned to different work")
            conn.execute("COMMIT")
            return old["id"]
        job_id = str(uuid.uuid4())
        conn.execute("INSERT INTO jobs(id,kind,payload,dedupe_key,status,created_at,updated_at) "
                     "VALUES(?,?,?,?,?,?,?)", (job_id, kind, raw, dedupe_key, "queued", now, now))
        _event(conn, job_id, "submitted", {"kind": kind}, now)
        conn.execute("COMMIT")
        return job_id
    except Exception:
        conn.execute("ROLLBACK")
        raise


def claim(conn: sqlite3.Connection, owner: str, now: float | None = None, *, allow_model_use=False, allow_native_import=False, allow_jane_library_create=False, jane_library_only=False,
          jane_queue_job_id=None, allow_omniroute_model_use=False, omniroute_queue_job_id=None, allow_terminal_probe=False,
          omni_max_24h=OMNI_MAX_24H):
    if omniroute_queue_job_id is not None and (not allow_omniroute_model_use or jane_library_only or jane_queue_job_id is not None):
        raise ValueError('Exact OmniRoute selector requires separate OmniRoute-only approval')
    if jane_queue_job_id is not None and not jane_library_only:
        raise ValueError('Job ID filter requires Jane library-only mode')
    if jane_library_only and not allow_jane_library_create:
        raise ValueError('Jane-only selector requires specific library creation approval')
    if not owner or len(owner) > 128:
        raise ValueError("Worker identifier required")
    if type(omni_max_24h) is not int or not 1 <= omni_max_24h <= 20:
        raise ValueError("OmniRoute rolling claim budget must be 1 to 20")
    now = time.time() if now is None else now
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Expired leases are safe to replay ONLY because the allowlist is read-only.
        expired = conn.execute("SELECT id,kind,attempts FROM jobs WHERE status='running' AND lease_until<=?", (now,)).fetchall()
        for row in expired:
            if row["kind"] in {RESEARCH_KIND, OMNI_KIND, NATIVE_KIND, LIBRARY_KIND, TERMINAL_KIND} or row["attempts"] >= MAX_ATTEMPTS:
                conn.execute("UPDATE jobs SET status='needs_review',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                             (now, row["id"]))
                _event(conn, row["id"], "exhausted_lease", {}, now)
            else:
                conn.execute("UPDATE jobs SET status='queued',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                             (now, row["id"]))
                _event(conn, row["id"], "requeued_expired_readonly_lease", {}, now)
        # Quota is enforced inside this SQLite IMMEDIATE transaction, so
        # concurrent worker processes cannot both claim the final allowance.
        omni_used = conn.execute(
            "SELECT COUNT(*) FROM events e JOIN jobs j ON e.job_id=j.id "
            "WHERE j.kind=? AND e.event='claimed' AND e.timestamp>=?",
            (OMNI_KIND, now - 86400)).fetchone()[0]
        # Fail closed after three consecutive, *recorded* failed OmniRoute
        # inference jobs. The read is inside BEGIN IMMEDIATE, shared by all
        # concurrent specialists; never retry old IDs or claim another job
        # merely because provider responses are failing. A validated usable
        # draft breaks the streak. An unknown review state does not falsely
        # count as a gateway failure.
        recent_omni = conn.execute(
            "SELECT j.status,j.result FROM events e JOIN jobs j ON e.job_id=j.id "
            "WHERE j.kind=? AND e.event='claimed' AND e.timestamp>=? "
            "ORDER BY e.timestamp DESC, e.id DESC LIMIT 3",
            (OMNI_KIND, now - 86400)).fetchall()
        consecutive_failed = 0
        for previous in recent_omni:
            try:
                outcome = json.loads(previous["result"]) if previous["result"] else {}
            except (ValueError, TypeError):
                outcome = {}
            failed_attempt = (previous["status"] == "failed" or
                              (isinstance(outcome, dict) and
                               outcome.get("draft_status") ==
                               "needs_review_no_auto_retry"))
            if not failed_attempt:
                break
            consecutive_failed += 1
        omni_circuit_open = consecutive_failed >= 3
        omni_enabled = (allow_omniroute_model_use and
                        omni_used < omni_max_24h and not omni_circuit_open)
        kinds = sorted(ALLOWED | ({RESEARCH_KIND} if allow_model_use else set())
                       | ({OMNI_KIND} if omni_enabled else set())
                       | ({NATIVE_KIND} if allow_native_import else set())
                       | ({LIBRARY_KIND} if allow_jane_library_create else set())
                       | ({TERMINAL_KIND} if allow_terminal_probe else set()))
        if jane_library_only:
            kinds = [LIBRARY_KIND]
        if omniroute_queue_job_id is not None:
            kinds = [OMNI_KIND] if omni_enabled else []
        selected_id = omniroute_queue_job_id if omniroute_queue_job_id is not None else jane_queue_job_id
        marks = ",".join("?" for _ in kinds)
        job_filter = " AND id=?" if selected_id is not None else ""
        args = [*kinds, selected_id] if selected_id is not None else kinds
        job = conn.execute(f"SELECT * FROM jobs WHERE status='queued' AND kind IN ({marks}){job_filter} ORDER BY created_at,id LIMIT 1", args).fetchone()
        if job:
            conn.execute("UPDATE jobs SET status='running',attempts=attempts+1,lease_owner=?,lease_until=?,updated_at=? WHERE id=?",
                         (owner, now + (420 if job['kind'] in {NATIVE_KIND, LIBRARY_KIND} else 360 if job["kind"] in {RESEARCH_KIND, OMNI_KIND} else LEASE_SECONDS), now, job["id"]))
            _event(conn, job["id"], "claimed", {"worker": owner, "attempt": job["attempts"]+1}, now)
        conn.execute("COMMIT")
        return dict(job) if job else None
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _relative_path(value: str) -> Path:
    if not value or "\\" in value:
        raise ValueError("Invalid relative inventory path")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Inventory path escapes workspace")
    return p


def inventory(workspace: Path, subpath: str) -> dict:
    workspace = Path(workspace).expanduser()
    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("Workspace must be an existing non-symlink directory")
    workspace = workspace.resolve(strict=True)
    requested = _relative_path(subpath)
    target = workspace / requested
    if target.is_symlink() or not target.is_dir():
        raise ValueError("Inventory target must be a real directory")
    target = target.resolve(strict=True)
    if not target.is_relative_to(workspace):
        raise ValueError("Inventory target escapes workspace")
    files = []
    for folder, dirs, names in os.walk(target, topdown=True, followlinks=False):
        here = Path(folder)
        depth = len(here.relative_to(target).parts)
        dirs[:] = sorted(d for d in dirs if not (here / d).is_symlink()) if depth < MAX_DEPTH else []
        for name in sorted(names):
            candidate = here / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if len(files) >= MAX_FILES:
                raise ValueError("Inventory exceeded file count limit")
            st = candidate.stat()
            files.append({"path": candidate.relative_to(workspace).as_posix(), "bytes": st.st_size})
    return {"workspace_subpath": requested.as_posix(), "file_count": len(files), "files": files,
            "read_only": True, "truncated_depth": MAX_DEPTH}


def macos_version_probe(*, run=subprocess.run, platform=None) -> dict:
    """One fixed, bounded, read-only macOS subprocess; never a remote shell."""
    host_platform = sys.platform if platform is None else platform
    if host_platform != "darwin":
        raise ValueError("Terminal probe requires the actual macOS host")
    try:
        proc = run(["/usr/bin/sw_vers", "-productVersion"],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   stdin=subprocess.DEVNULL, cwd="/",
                   env={"PATH": "/usr/bin:/bin"}, timeout=8, check=False,
                   text=True)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("Fixed macOS version probe failed") from None
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        raise ValueError("Fixed macOS version probe was unsuccessful")
    version = proc.stdout.strip()
    if len(version) > 32 or re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3}){1,2}", version) is None:
        raise ValueError("Invalid sanitized macOS version result")
    return {"ok": True, "read_only": True, "command_id": "macos-version",
            "macos_version": version, "terminal_subprocess_verified": True}


def run_once(conn: sqlite3.Connection, workspace: Path, owner: str = "local-worker", now: float | None = None, *, allow_model_use=False, allow_native_import=False, allow_jane_library_create=False, jane_library_only=False,
             jane_queue_job_id=None, allow_omniroute_model_use=False, omniroute_queue_job_id=None, allow_terminal_probe=False,
             omni_max_24h=OMNI_MAX_24H):
    state = Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent
    if os.path.lexists(state / "STOP"):
        return None
    job = claim(conn, owner, now, allow_model_use=allow_model_use, allow_native_import=allow_native_import,
                allow_jane_library_create=allow_jane_library_create,
                jane_library_only=jane_library_only,
                jane_queue_job_id=jane_queue_job_id,
                allow_omniroute_model_use=allow_omniroute_model_use,
                omniroute_queue_job_id=omniroute_queue_job_id,
                 allow_terminal_probe=allow_terminal_probe,
                 omni_max_24h=omni_max_24h)
    if not job:
        return None
    job_id, kind = job["id"], job["kind"]
    t = time.time() if now is None else now
    try:
        payload = json.loads(job["payload"])
        if kind == "system.ping":
            result = {"ok": True, "read_only": True}
        elif kind == TERMINAL_KIND:
            if not allow_terminal_probe or os.path.lexists(state / "STOP"):
                raise ValueError("Terminal probe not approved or stopped")
            result = macos_version_probe()
        elif kind == "system.omniroute-preflight":
            import ghost_omniroute_job
            result = ghost_omniroute_job.background_preflight()
        elif kind == RESEARCH_KIND:
            import interpreter_host_job
            output = state / ("research-" + job_id)
            rc = interpreter_host_job.main(['--run', '--approve-model-use', '--follow-up',
                    '--output', str(output), '--stop-file', str(state / 'STOP')])
            receipt = output / 'receipts/jane-finalcut-host-001.receipt.json'
            report = json.loads(receipt.read_text())
            if rc or report['status'] != 'completed_unverified':
                raise ValueError('Research did not complete; inspect private receipt: ' + str(receipt))
            result = {"research_receipt": str(receipt), "answer_sha256": report['answer_sha256'],
                      "facts_verified": False, "app_control_verified": False}
        elif kind == OMNI_KIND:
            if not allow_omniroute_model_use:
                raise ValueError('OmniRoute requires separate explicit approval')
            import ghost_omniroute_job
            result = ghost_omniroute_job.execute(
                state, job_id, payload, stop_path=state / 'STOP')
            # A provider-produced memo is never automatically approved. Even
            # an HTTP 200 / nonempty answer remains a review-required draft.
            conn.execute('BEGIN IMMEDIATE')
            changed = conn.execute(
                "UPDATE jobs SET status='needs_review',result=?,error=NULL,"
                "lease_owner=NULL,lease_until=NULL,updated_at=? "
                "WHERE id=? AND status='running' AND lease_owner=?",
                (json.dumps(result, sort_keys=True), t, job_id, owner)).rowcount
            if changed != 1:
                raise ValueError('Lost OmniRoute job ownership')
            _event(conn, job_id, 'needs_review',
                   {'kind': kind, 'draft_status': result['draft_status']}, t)
            conn.execute('COMMIT')
            return {'id': job_id, 'status': 'needs_review', 'result': result}
        elif kind == "files.inventory":
            result = inventory(workspace, payload.get("subpath", "."))
        elif kind == LIBRARY_KIND:
            if not allow_jane_library_create:
                raise ValueError('Explicit Jane library creation approval missing')
            # STOP may have appeared after SQLite claim and before GUI work.
            # Never proceed or auto-replay on that race.
            if os.path.lexists(state / 'STOP'):
                raise ValueError('STOP requested before Jane native GUI dispatch')
            if sys.platform != 'darwin':
                raise ValueError('Jane native GUI creation only allowed on macOS host')
            import fcp_jane_library_onepass as jane
            result = jane.onepass(Path.home(), payload['job_id'], create=True)
            # Creating a bundle on disk is NOT evidence FCP selected it.
            # No native GUI action is ever automatically retried, including
            # when a process crashes after click Save.
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                "UPDATE jobs SET status='needs_review',result=?,error=NULL,lease_owner=NULL,lease_until=NULL,updated_at=? "
                "WHERE id=? AND status='running' AND lease_owner=?",
                (json.dumps(result, sort_keys=True), t, job_id, owner)).rowcount
            if updated != 1:
                raise ValueError('Lost Jane job ownership; inspect existing native receipt')
            _event(conn, job_id, 'needs_review',
                   {'kind': kind, 'native_status': result.get('status'),
                    'app_selection_verified': False}, t)
            conn.execute('COMMIT')
            return {'id': job_id, 'status': 'needs_review', 'result': result}
        elif kind == NATIVE_KIND:
            raise ValueError(NATIVE_DISABLED_REASON)
        else:
            raise ValueError("Adapter disabled; no execution")
        conn.execute("BEGIN IMMEDIATE")
        updated = conn.execute("UPDATE jobs SET status='succeeded',result=?,error=NULL,lease_owner=NULL,lease_until=NULL,updated_at=? "
                               "WHERE id=? AND status='running' AND lease_owner=?",
                               (json.dumps(result, sort_keys=True), t, job_id, owner)).rowcount
        if updated != 1:
            raise ValueError("Lost job ownership; result not committed")
        _event(conn, job_id, "succeeded", {"kind": kind}, t)
        conn.execute("COMMIT")
        return {"id": job_id, "status": "succeeded", "result": result}
    except Exception as exc:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        conn.execute("BEGIN IMMEDIATE")
        terminal = 'needs_review' if kind in {NATIVE_KIND, LIBRARY_KIND, OMNI_KIND, TERMINAL_KIND} else 'failed'
        conn.execute("UPDATE jobs SET status=?,error=?,lease_owner=NULL,lease_until=NULL,updated_at=? "
                     "WHERE id=? AND status='running' AND lease_owner=?", (terminal, str(exc), t, job_id, owner))
        _event(conn, job_id, terminal, {"error": type(exc).__name__}, t)
        conn.execute("COMMIT")
        return {"id": job_id, "status": terminal, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="Private persistent state directory, outside source checkout")
    parser.add_argument("--workspace", type=Path, required=True, help="Authorized directory to inventory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    add = sub.add_parser("enqueue")
    add.add_argument("--kind", required=True)
    add.add_argument("--payload", default="{}")
    add.add_argument("--key", required=True)
    run = sub.add_parser("run-once")
    run.add_argument("--worker-id", default="local-worker")
    run.add_argument("--approve-model-use", action="store_true")
    run.add_argument("--approve-omniroute-model-use", action="store_true",
                     help="Separate approval; max five private OmniRoute jobs per rolling 24h")
    run.add_argument("--allow-native-import", action="store_true")
    run.add_argument("--approve-jane-library-create", action="store_true",
                     help="One explicit Mac GUI library creation; does not import XML")
    sub.add_parser("status")
    args = parser.parse_args()
    with connect(args.state) as conn:
        if args.command == "init":
            output = {"initialized": True, "allowed_jobs": sorted(ALLOWED), "opt_in_model_jobs": [RESEARCH_KIND, OMNI_KIND], "opt_in_native_jobs": [LIBRARY_KIND], "disabled_adapters": sorted(FUTURE_DISABLED | {NATIVE_KIND})}
        elif args.command == "enqueue":
            output = {"id": enqueue(conn, args.kind, json.loads(args.payload), args.key)}
        elif args.command == "run-once":
            output = run_once(conn, args.workspace, args.worker_id, allow_model_use=args.approve_model_use,
                              allow_native_import=args.allow_native_import,
                              allow_jane_library_create=args.approve_jane_library_create,
                              allow_omniroute_model_use=args.approve_omniroute_model_use)
        else:
            rows = conn.execute("SELECT id,kind,status,attempts,error FROM jobs ORDER BY created_at,id").fetchall()
            output = {"jobs": [dict(r) for r in rows]}
        print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

