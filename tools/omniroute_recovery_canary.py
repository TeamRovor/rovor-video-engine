#!/usr/bin/env python3
"""Explicit one-job ROVOR recovery canary for the EXISTING Mac SQLite queue.

Default is read-only: no model call. With both owner flags, this may submit
one NEW, bounded, review-only v2 packet and claim ONLY its exact UUID despite
an older failed-job circuit. The claim still obeys the previously authorized
14-per-rolling-day quota, STOP and pinned :free OpenRouter route. Never retry
historical job IDs, auto-approve drafts, change the LaunchAgent or model routes.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path

import ghost_worker as worker
import ghost_omniroute_feed as feed
import ghost_omniroute_job as omni
import omniroute_workpack_runner as workpack

STATE = Path.home() / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"
ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path.home() / "Documents/Rovor"
MAX_OWNER_BUDGET = 14
CLEAN = {"draft_completed_needs_review", "needs_review_no_auto_retry",
         "reserved_no_retry", "previous_attempt_not_replayed"}
REVIEW = {"draft_ready_for_human_review", "failed_needs_review",
          "incomplete_needs_review", "invalid_receipt",
          "content_quality_needs_review", "execution_claim_needs_review",
          "sensitive_draft_blocked", "stale_source"}


def run(*, approve=False, acknowledge_circuit=False,
        state=STATE, root=ROOT, workspace=WORKSPACE,
        get_db=None, read_combo=None, runner=None):
    result = {"kind": "one_new_omniroute_recovery_canary",
              "model_request_allowed": False,
              "historical_jobs_replayed": False,
              "previous_receipts_modified": False,
              "automatic_publication": False,
              "status": "requires_both_owner_approvals",
              "source_revision_only": True}
    if not (approve and acknowledge_circuit):
        return result
    state = Path(state)
    if os.path.lexists(state / "STOP"):
        result["status"] = "owner_stop_present"
        return result
    if (not state.is_dir() or state.is_symlink()
            or not (state / "jobs.sqlite3").is_file()
            or not Path(workspace).is_dir()):
        result["status"] = "existing_worker_state_not_verified"
        return result
    try:
        # Verify before a single DB write. This is a local CLI read, not
        # a model request. Never return raw CLI output or credentials.
        if read_combo is None: read_combo = omni.read_combo_catalog
        omni.verify_route(feed.RECOVERY_CANARY[0], read_combo())
        workpack.load_packet(Path(root), feed.RECOVERY_CANARY[0])
    except (OSError, ValueError, KeyError, TypeError):
        result["status"] = "reviewed_route_or_packet_not_verified"
        return result
    if get_db is None: get_db = worker.connect
    if runner is None: runner = worker.run_once
    try:
        with closing(get_db(state)) as conn:
            if os.path.lexists(state / "STOP"):
                result["status"] = "owner_stop_present"
                return result
            canary = feed.RECOVERY_CANARY
            row = conn.execute(
                "SELECT id,status FROM jobs WHERE dedupe_key=?",
                (canary[1],)).fetchone()
            if not row:
                seeded = feed.feed_recovery(conn, state, root, limit=1)
                if seeded.get("status") != "recovery_canary_queued":
                    result["status"] = "other_pending_work_blocks_recovery"
                    return result
                row = conn.execute(
                    "SELECT id,status FROM jobs WHERE dedupe_key=?",
                    (canary[1],)).fetchone()
            if row["status"] != "queued":
                result["status"] = "canary_already_claimed_never_retry"
                return result
            result["model_request_allowed"] = True
            # Transactional, exact-UUID claim; the only circuit exception.
            # The same shared SQLite daily quota and STOP checks still apply.
            receipt = runner(
                conn, workspace, owner="rovor-approved-one-recovery-canary",
                allow_omniroute_model_use=True,
                omniroute_queue_job_id=row["id"],
                allow_recovery_canary=True,
                omni_max_24h=MAX_OWNER_BUDGET)
            if receipt is None:
                result["status"] = "no_claim_circuit_quota_or_stop"
                return result
            detail = receipt.get("result") or {}
            draft = detail.get("draft_status")
            review = detail.get("review_status")
            result["status"] = "completed_requires_human_review" if (
                draft == "draft_completed_needs_review" and
                review == "draft_ready_for_human_review") else "completed_not_review_ready"
            result["new_claim_recorded"] = True
            result["draft_status"] = draft if draft in CLEAN else "unavailable"
            result["review_status"] = review if review in REVIEW else "unavailable"
            result["model_request_count"] = 1
            return result
    except (OSError, ValueError, TypeError):
        result["status"] = "canary_blocked_or_unavailable"
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-one-recovery-model-job", action="store_true",
                        help="Allow one NEW, finite, review-only canary, not a replay")
    parser.add_argument("--acknowledge-open-circuit", action="store_true",
                        help="Explicitly allow only the selected canary through the claim circuit")
    args = parser.parse_args()
    print(json.dumps(run(approve=args.approve_one_recovery_model_job,
                         acknowledge_circuit=args.acknowledge_open_circuit),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
