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
                # Sanitized evidence only: never show raw model text, saved
                # receipt paths, user prompts, arbitrary errors, or API keys.
                failure_states = Counter()
                failure_elapsed = Counter()
                role_counts = {r:Counter() for r in ROLES}
                for row in conn.execute(
                        "SELECT id,payload,status,result FROM jobs WHERE kind='research.omniroute'"):
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
                        status = outcome.get("draft_status")
                        review = outcome.get("review_status")
                        approved_status = {"needs_review_no_auto_retry",
                                           "previous_attempt_not_replayed",
                                           "concurrent_attempt_not_replayed"}
                        approved_review = {"failed_needs_review",
                                           "incomplete_needs_review",
                                           "invalid_receipt", "stale_source",
                                           "content_quality_needs_review",
                                           "execution_claim_needs_review",
                                           "sensitive_draft_blocked"}
                        if status in approved_status:
                            failure_states["draft:" + status] += 1
                        else:
                            failure_states["draft:other_nonready"] += 1
                        if review in approved_review:
                            failure_states["review:" + review] += 1
                        elif review:
                            failure_states["review:other_nonready"] += 1
                        # Read only the exact job's fixed-name private receipt.
                        # Whitelist values, not attacker/provider-controlled data.
                        uid = row["id"]
                        if (isinstance(uid, str) and len(uid) == 36
                                and all(ch in "0123456789abcdef-" for ch in uid)
                                and isinstance(packet, str)
                                and packet in {slug for group in ROLE_PACKET.values()
                                               for slug in group}):
                            folder = state / "omniroute-drafts" / uid
                            receipt = folder / (packet + ".receipt.json")
                            if (not folder.is_symlink() and folder.is_dir()
                                    and not receipt.is_symlink()
                                    and receipt.is_file()
                                    and receipt.stat().st_size <= 60000):
                                try:
                                    saved = json.loads(receipt.read_bytes())
                                except (OSError, ValueError, UnicodeError):
                                    saved = None
                                if (isinstance(saved, dict)
                                        and saved.get("id") == packet.replace("walter-v1-", "walter-public-v1-")
                                        and saved.get("status") == status):
                                    error_class = saved.get("error_class")
                                    allowed_errors = {"ValueError", "TimeoutError",
                                        "HTTPError", "URLError", "OSError",
                                        "IndexError", "RuntimeError", "TypeError"}
                                    if error_class in allowed_errors:
                                        failure_states["exception:" + error_class] += 1
                                    seconds = saved.get("elapsed_seconds")
                                    if type(seconds) in (int, float) and 0 <= seconds <= 3600:
                                        bucket = ("under_1s" if seconds < 1 else
                                                  "1_to_15s" if seconds < 15 else
                                                  "15_to_60s" if seconds < 60 else
                                                  "60_to_120s" if seconds < 120 else
                                                  "over_120s")
                                        failure_elapsed[bucket] += 1
                result["omniroute_draft_counts"] = dict(stats)
                result["nonready_reason_counts"] = dict(failure_states)
                result["nonready_elapsed_buckets"] = dict(failure_elapsed)
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
