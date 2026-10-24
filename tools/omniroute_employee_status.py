#!/usr/bin/env python3
"""Read-only ROVOR OmniRoute crew status. No credential reads or inference."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

LABEL = "com.rovor.ghost-worker.readonly"
DEFAULT_STATE = Path.home() / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"
ROLES = ("mike", "jane", "jesse", "gale", "gus", "saul", "hank")


def inspect(state, *, run=subprocess.run):
    state = Path(state).expanduser()
    result = {
        "worker_kind": "omniroute_existing_launchagent",
        "live_model_inference_verified_by_this_probe": False,
        "private_model_text_exposed": False,
        "credential_access_attempted": False,
        "stop_requested": (state / "STOP").exists(),
    }
    try:
        proc = run(["/bin/launchctl", "print",
                    "gui/{}/{}".format(os.getuid(), LABEL)],
                   capture_output=True, text=True, timeout=8, check=False)
        result["launchagent_loaded"] = proc.returncode == 0
        if proc.returncode == 0:
            for line in (proc.stdout or "").splitlines():
                clean = line.strip()
                for key in ("runs", "last exit code"):
                    if clean.startswith(key + " = "):
                        value = clean.partition(" = ")[2]
                        if value.isdecimal():
                            result[key.replace(" ", "_")] = int(value)
    except (OSError, subprocess.TimeoutExpired):
        result["launchagent_loaded"] = False
    if state.is_symlink() or not state.is_dir():
        result["database_status"] = "state_missing_or_redirected"
        return result
    db = state / "jobs.sqlite3"
    if db.is_symlink() or not db.is_file():
        result["database_status"] = "database_missing_or_redirected"
        return result
    # WAL sidecars are expected for a running SQLite worker. Their presence
    # must not hide the very receipts we are trying to verify. Never copy
    # the live WAL/main files independently, as that could silently omit
    # committed jobs. An online, read-only SQLite backup is consistent.
    sidecars = []
    for suffix in ("-wal", "-shm"):
        side = state / ("jobs.sqlite3" + suffix)
        if side.is_symlink() or (side.exists() and not side.is_file()):
            result["database_status"] = "unsafe_database_sidecar"
            return result
        sidecars.append(side.exists())
    if any(sidecars) and not all(sidecars):
        result["database_status"] = "incomplete_wal_sidecars"
        return result
    try:
        with tempfile.TemporaryDirectory(prefix="rovor-status-") as tmp:
            snapshot = Path(tmp) / "snapshot.sqlite3"
            if all(sidecars):
                # Never write to live DB. A read-only source connection copies
                # one transactionally consistent view into a private temp DB.
                with sqlite3.connect(db.as_uri() + "?mode=ro",
                                     uri=True, timeout=6) as source:
                    source.execute("PRAGMA query_only=ON")
                    with sqlite3.connect(str(snapshot), timeout=6) as destination:
                        source.backup(destination, pages=64, sleep=0.05)
            else:
                # With no WAL sidecars the historical worker snapshot is
                # safely copyable. Preserve the existing no-write fallback,
                # including WAL-header databases with no live sidecars.
                before = db.stat()
                shutil.copyfile(db, snapshot)
                after = db.stat()
                if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                    result["database_status"] = "database_changed_during_snapshot"
                    return result
            conn = sqlite3.connect(str(snapshot))
            conn.row_factory = sqlite3.Row
            try:
                result["database_integrity"] = conn.execute(
                    "PRAGMA integrity_check").fetchone()[0]
                counts = conn.execute(
                    "SELECT kind, status, COUNT(*) AS n FROM jobs GROUP BY kind, status"
                ).fetchall()
                result["job_status_counts"] = [
                    {"kind":row["kind"],"status":row["status"],"count":row["n"]}
                    for row in counts]
                stats = Counter()
                role_counts = {r:Counter() for r in ROLES}
                for row in conn.execute(
                        "SELECT payload,status,result FROM jobs WHERE kind='research.omniroute'"):
                    try:
                        payload = json.loads(row["payload"])
                        outcome = json.loads(row["result"]) if row["result"] else {}
                    except (ValueError, TypeError):
                        continue
                    packet = payload.get("packet") if isinstance(payload, dict) else None
                    if isinstance(packet, str) and packet.startswith("walter-v1-"):
                        for role in ROLES:
                            if packet in ROLE_PACKET[role]:
                                role_counts[role][row["status"]] += 1
                                break
                    if (isinstance(outcome, dict)
                            and outcome.get("draft_status") == "draft_completed_needs_review"
                            and outcome.get("review_status") == "draft_ready_for_human_review"):
                        stats["review_ready"] += 1
                    elif isinstance(outcome, dict) and outcome.get("draft_status"):
                        stats["model_attempt_not_review_ready"] += 1
                result["omniroute_draft_counts"] = dict(stats)
                result["specialists"] = {
                    role:dict(counts) for role,counts in role_counts.items()
                }
                since=time.time()-86400
                result["ai_claims_last_24h"] = conn.execute(
                    "SELECT COUNT(*) FROM events e JOIN jobs j ON j.id=e.job_id "
                    "WHERE j.kind='research.omniroute' AND e.event='claimed' "
                    "AND e.timestamp>=?",(since,)).fetchone()[0]
                result["database_status"] = "snapshot_readable"
            finally:
                conn.close()
    except (OSError, sqlite3.Error):
        result["database_status"] = "snapshot_unavailable"
    return result


ROLE_PACKET = {
    "mike": ("walter-v1-mac-worker-stop-recovery", "walter-v1-omniroute-failure-boundaries"),
    "jane": ("walter-v1-finalcut-source-first-process", "walter-v1-fcpxml-handoff-acceptance"),
    "jesse": ("walter-v1-moho-viseme-review", "walter-v1-animation-checkpoints"),
    "gale": ("walter-v1-blender-isolation-plan", "walter-v1-render-confidence-rubric"),
    "gus": ("walter-v1-safe-client-intake", "walter-v1-business-delivery-checkpoints"),
    "saul": ("walter-v1-outreach-draft-review", "walter-v1-social-content-safety"),
    "hank": ("walter-v1-proof-before-done", "walter-v1-free-route-usage-audit"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print(json.dumps(inspect(args.state), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
