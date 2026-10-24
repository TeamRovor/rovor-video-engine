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
                v2_states = {}
                v2_slug_to_role = {
                    "walter-v2-" + role + suffix:role
                    for role,suffix in (
                        ("mike","-worker-guard"),
                        ("jane","-editor-handoff"),
                        ("jesse","-animation-qa"),
                        ("gale","-render-qa"),
                        ("gus","-business-ops"),
                        ("saul","-review-ops"),
                        ("hank","-evidence-audit"))
                }
                for row in conn.execute(
                        "SELECT id,payload,status,result FROM jobs WHERE kind='research.omniroute'"):
                    try:
                        payload = json.loads(row["payload"])
                        outcome = json.loads(row["result"]) if row["result"] else {}
                    except (ValueError, TypeError):
                        continue
                    packet = payload.get("packet") if isinstance(payload, dict) else None
                    if isinstance(packet, str) and packet.startswith(("walter-v1-", "walter-v2-")):
                        for role in ROLES:
                            if packet in ROLE_PACKET[role]:
                                role_counts[role][row["status"]] += 1
                                break
                    if isinstance(packet, str) and packet in v2_slug_to_role:
                        role=v2_slug_to_role[packet]
                        evidence=(
                            isinstance(outcome,dict) and
                            outcome.get("draft_status") == "draft_completed_needs_review" and
                            outcome.get("review_status") == "draft_ready_for_human_review")
                        failed=(
                            row["status"] == "failed" or
                            (isinstance(outcome,dict) and
                             outcome.get("draft_status") == "needs_review_no_auto_retry"))
                        # A running job is never a completed model result.
                        # This view covers only the new v2 wave, not the older
                        # needs_review v1 failures which share these role names.
                        v2_states[role] = {
                            "job_status": row["status"] if row["status"] in (
                                "queued","running","needs_review",
                                "succeeded","failed") else "unavailable",
                            "review_ready":bool(evidence),
                            "failed_no_retry":bool(failed),
                            "review_state": (
                                outcome.get("review_status")
                                if isinstance(outcome,dict)
                                and outcome.get("review_status") in {
                                    "draft_ready_for_human_review",
                                    "failed_needs_review",
                                    "incomplete_needs_review",
                                    "invalid_receipt",
                                    "stale_source",
                                    "content_quality_needs_review",
                                    "execution_claim_needs_review",
                                    "sensitive_draft_blocked",
                                }
                                else "not_available"),
                            "failure_class": "not_available",
                            "admission_code": "not_available",
                        }
                    if packet == "walter-v2-recovery-proof":
                        result["recovery_canary"] = {
                            "status": row["status"] if row["status"] in
                                      ("queued", "running", "needs_review",
                                       "succeeded", "failed") else "unavailable",
                            "review_ready": (
                                isinstance(outcome, dict) and
                                outcome.get("draft_status") == "draft_completed_needs_review" and
                                outcome.get("review_status") == "draft_ready_for_human_review")}
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
                                        and saved.get("id") == (
                                            packet.replace("walter-v1-", "walter-public-v1-", 1)
                                            .replace("walter-v2-", "walter-public-v2-", 1))
                                        and saved.get("status") == status):
                                    error_class = saved.get("error_class")
                                    # The receipt writer stores only
                                    # type(exc).__name__, not an exception
                                    # message or provider response. An
                                    # allowlist hid most real Mac failures:
                                    # display any *strictly valid* bounded
                                    # Python class identifier instead, with
                                    # no provider-controlled punctuation.
                                    if (type(error_class) is str
                                            and 1 <= len(error_class) <= 48
                                            and error_class.isascii()
                                            and error_class.isidentifier()):
                                        failure_states["exception:" + error_class] += 1
                                        if packet in v2_slug_to_role:
                                            v2_states[v2_slug_to_role[packet]][
                                                "failure_class"] = error_class
                                    else:
                                        failure_states["exception:unavailable"] += 1
                                    # Fixed source-code error keys only; never
                                    # render raw gateway or provider messages.
                                    reason = saved.get("admission_code")
                                    allowed_reason = {
                                        "invalid_response_shape", "invalid_usage_shape",
                                        "reasoning_budget_exhausted",
                                        "incomplete_length_stop",
                                        "unapproved_finish_reason",
                                        "empty_visible_output",
                                        "output_exceeds_review_limit",
                                        "invalid_model_completion"}
                                    if type(reason) is str and reason in allowed_reason:
                                        failure_states["admission:" + reason] += 1
                                        if packet in v2_slug_to_role:
                                            v2_states[v2_slug_to_role[packet]][
                                                "admission_code"] = reason
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
                result["v2_recovery_specialists"] = {
                    role:v2_states.get(role,{"job_status":"not_queued",
                                             "review_ready":False,
                                             "failed_no_retry":False,
                                             "review_state":"not_available",
                                             "failure_class":"not_available",
                                             "admission_code":"not_available"})
                    for role in ROLES}
                result["v2_recovery_summary"] = {
                    "queued":sum(x["job_status"]=="queued" for x in v2_states.values()),
                    "running":sum(x["job_status"]=="running" for x in v2_states.values()),
                    "review_ready":sum(x["review_ready"] for x in v2_states.values()),
                    "failed_no_retry":sum(x["failed_no_retry"] for x in v2_states.values()),
                    "not_queued":len(ROLES)-len(v2_states),
                }
                since=time.time()-86400
                result["ai_claims_last_24h"] = conn.execute(
                    "SELECT COUNT(*) FROM events e JOIN jobs j ON j.id=e.job_id "
                    "WHERE j.kind='research.omniroute' AND e.event='claimed' "
                    "AND e.timestamp>=?",(since,)).fetchone()[0]
                recent = conn.execute(
                    "SELECT j.status,j.result FROM events e JOIN jobs j "
                    "ON j.id=e.job_id WHERE j.kind='research.omniroute' "
                    "AND e.event='claimed' AND e.timestamp>=? "
                    "ORDER BY e.timestamp DESC,e.rowid DESC LIMIT 3",
                    (since,)).fetchall()
                failed_recent = 0
                for previous in recent:
                    try:
                        outcome = (json.loads(previous["result"])
                                   if previous["result"] else {})
                    except (TypeError, ValueError):
                        outcome = {}
                    if (previous["status"] == "failed" or
                            (isinstance(outcome, dict) and
                             outcome.get("draft_status") == "needs_review_no_auto_retry")):
                        failed_recent += 1
                    else:
                        break
                result["consecutive_recorded_inference_failures"] = failed_recent
                result["inference_claim_guard_would_block"] = failed_recent >= 3
                result["database_status"] = "snapshot_readable"
            finally:
                conn.close()
    except (OSError, sqlite3.Error):
        result["database_status"] = "snapshot_unavailable"
    return result


ROLE_PACKET = {
    "mike": ("walter-v1-mac-worker-stop-recovery", "walter-v1-omniroute-failure-boundaries", "walter-v2-mike-worker-guard"),
    "jane": ("walter-v1-finalcut-source-first-process", "walter-v1-fcpxml-handoff-acceptance", "walter-v2-jane-editor-handoff"),
    "jesse": ("walter-v1-moho-viseme-review", "walter-v1-animation-checkpoints", "walter-v2-jesse-animation-qa"),
    "gale": ("walter-v1-blender-isolation-plan", "walter-v1-render-confidence-rubric", "walter-v2-gale-render-qa"),
    "gus": ("walter-v1-safe-client-intake", "walter-v1-business-delivery-checkpoints", "walter-v2-gus-business-ops"),
    "saul": ("walter-v1-outreach-draft-review", "walter-v1-social-content-safety", "walter-v2-saul-review-ops"),
    "hank": ("walter-v1-proof-before-done", "walter-v1-free-route-usage-audit",
             "walter-v2-hank-evidence-audit"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print(json.dumps(inspect(args.state), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
