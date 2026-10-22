#!/usr/bin/env python3
"""ROVOR durable job executor with read-only defaults and opt-in native import.

This job database records *execution jobs*, not GitHub development task ownership.
Native Final Cut diagnostic import is separately opt-in. No mail/publishing adapters.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

ALLOWED = frozenset({"system.ping", "files.inventory"})
FUTURE_DISABLED = frozenset({
    "blender.scene", "moho.animate", "finalcut.timeline", "email.read",
    "email.send", "social.publish", "files.move", "files.delete",
})
RESEARCH_KIND = "research.finalcut"
NATIVE_KIND = "finalcut.import-diagnostic"
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
    if kind not in ALLOWED | {RESEARCH_KIND, NATIVE_KIND}:
        raise ValueError(f"Adapter disabled or unknown: {kind}")
    if not isinstance(payload, dict) or not isinstance(dedupe_key, str) or not (1 <= len(dedupe_key) <= 200):
        raise ValueError("A JSON-object payload and nonempty dedupe key (max 200) are required")
    if kind in {"system.ping", RESEARCH_KIND} and payload:
        raise ValueError("This fixed job does not accept parameters")
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


def claim(conn: sqlite3.Connection, owner: str, now: float | None = None, *, allow_model_use=False, allow_native_import=False):
    if not owner or len(owner) > 128:
        raise ValueError("Worker identifier required")
    now = time.time() if now is None else now
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Expired leases are safe to replay ONLY because the allowlist is read-only.
        expired = conn.execute("SELECT id,kind,attempts FROM jobs WHERE status='running' AND lease_until<=?", (now,)).fetchall()
        for row in expired:
            if row["kind"] in {RESEARCH_KIND, NATIVE_KIND} or row["attempts"] >= MAX_ATTEMPTS:
                conn.execute("UPDATE jobs SET status='needs_review',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                             (now, row["id"]))
                _event(conn, row["id"], "exhausted_lease", {}, now)
            else:
                conn.execute("UPDATE jobs SET status='queued',lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                             (now, row["id"]))
                _event(conn, row["id"], "requeued_expired_readonly_lease", {}, now)
        kinds = sorted(ALLOWED | ({RESEARCH_KIND} if allow_model_use else set())
                       | ({NATIVE_KIND} if allow_native_import else set()))
        marks = ",".join("?" for _ in kinds)
        job = conn.execute(f"SELECT * FROM jobs WHERE status='queued' AND kind IN ({marks}) ORDER BY created_at,id LIMIT 1", kinds).fetchone()
        if job:
            conn.execute("UPDATE jobs SET status='running',attempts=attempts+1,lease_owner=?,lease_until=?,updated_at=? WHERE id=?",
                         (owner, now + (420 if job['kind'] == NATIVE_KIND else 360 if job["kind"] == RESEARCH_KIND else LEASE_SECONDS), now, job["id"]))
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


def run_once(conn: sqlite3.Connection, workspace: Path, owner: str = "local-worker", now: float | None = None, *, allow_model_use=False, allow_native_import=False):
    state = Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent
    if os.path.lexists(state / "STOP"):
        return None
    job = claim(conn, owner, now, allow_model_use=allow_model_use, allow_native_import=allow_native_import)
    if not job:
        return None
    job_id, kind = job["id"], job["kind"]
    t = time.time() if now is None else now
    try:
        payload = json.loads(job["payload"])
        if kind == "system.ping":
            result = {"ok": True, "read_only": True}
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
        elif kind == "files.inventory":
            result = inventory(workspace, payload.get("subpath", "."))
        elif kind == NATIVE_KIND:
            import fcp_native_auto_import as native
            root = Path(workspace).expanduser().resolve(strict=True)
            requested = root / _relative_path(payload['candidates'])
            if requested.is_symlink() or not requested.is_dir():
                raise ValueError('Candidates must be an existing real directory')
            candidates = requested.resolve(strict=True)
            if not candidates.is_relative_to(root):
                raise ValueError('Candidates escape authorized workspace')
            output = root / ('native-import-' + job_id)
            report = native.prepare(candidates, output)
            report = native.dispatch(output, report, stop_file=state / 'STOP')
            if report['status'] != 'apple_events_sent_timeline_unverified':
                raise ValueError('Native import incomplete; inspect receipt: ' + str(output))
            result = {'native_receipt': str(output / 'native-auto-import-receipt.json'),
                      'native_timeline_verified': False, 'model_turn_started': False,
                      'dispatch_completed': True}
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
        terminal = 'needs_review' if kind == NATIVE_KIND else 'failed'
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
    run.add_argument("--allow-native-import", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args()
    with connect(args.state) as conn:
        if args.command == "init":
            output = {"initialized": True, "allowed_jobs": sorted(ALLOWED), "opt_in_model_jobs": [RESEARCH_KIND], "opt_in_native_jobs": [NATIVE_KIND], "disabled_adapters": sorted(FUTURE_DISABLED)}
        elif args.command == "enqueue":
            output = {"id": enqueue(conn, args.kind, json.loads(args.payload), args.key)}
        elif args.command == "run-once":
            output = run_once(conn, args.workspace, args.worker_id, allow_model_use=args.approve_model_use,
                              allow_native_import=args.allow_native_import)
        else:
            rows = conn.execute("SELECT id,kind,status,attempts,error FROM jobs ORDER BY created_at,id").fetchall()
            output = {"jobs": [dict(r) for r in rows]}
        print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

