#!/usr/bin/env python3
"""Inert public-grounding -> private-receipt -> specialist-coverage handoff.

This composes existing reviewed gates, not a new task queue or worker.
The caller MUST independently authenticate a single pinned public Git tree,
a consistent complete private SQLite jobs/claims copy, the job-to-role/task
mapping, and separate human review decisions. Boolean trust arguments are
caller attestations, NOT authentication performed here. Never feed model
assertions back as trust evidence. No network, provider, Mac or SQLite I/O.
"""
import hashlib
import re

from walter_public_task_grounding import GroundingError, select
from walter_real_receipt_bridge import BridgeError, prepare
from walter_specialist_coverage import CoverageError, choose

MAX_TASKS = 500
MAX_PUBLIC_SOURCES = 500
MAX_PUBLIC_BYTES = 4000000
SHA = re.compile(r"^[0-9a-f]{64}$")


def _refuse(status):
    return {"status": status, "candidate": None,
            "model_calls": 0, "queue_writes": 0, "mac_execution": False}


def propose(queue, routing, *, commit, source_bytes, source_digests,
            jobs, claims, job_roles, job_tasks, human_reviews, now,
            stop_present=True, other_job_running=True, owner_opt_in=False,
            trusted_pinned_snapshot=False, trusted_sqlite_copy=False,
            trusted_role_mapping=False, trusted_human_reviews=False,
            complete_ledger=False, trusted_task_mapping=False,
            approved_active_ids=(), trusted_owner_approval=False):
    """Return ONE public-only, unsubmitted proposal or a content-free refusal.

    A complete authenticated job_id -> task_id map is mandatory here, unlike
    the lower-level legacy coverage preview: it prevents replay across source
    revisions, dedupe changes and queued jobs. The caller MUST independently
    recheck STOP, leases, quotas, free billing eligibility and atomic SQLite
    claim at any later dispatch. This function never grants dispatch authority.
    """
    if stop_present is not False:
        return _refuse("stopped")
    if (owner_opt_in is not True or other_job_running is not False
            or any(flag is not True for flag in (
                trusted_pinned_snapshot, trusted_sqlite_copy,
                trusted_role_mapping, trusted_human_reviews,
                complete_ledger))):
        return _refuse("unverified_authority")
    if trusted_task_mapping is not True or type(job_tasks) is not dict:
        return _refuse("task_identity_ledger_unverified")
    try:
        if (type(queue) is not dict or type(queue.get("tasks")) is not list
                or len(queue["tasks"]) > MAX_TASKS
                or type(source_bytes) is not dict
                or type(source_digests) is not dict
                or set(source_bytes) != set(source_digests)
                or len(source_bytes) > MAX_PUBLIC_SOURCES):
            return _refuse("invalid_pinned_public_snapshot")
        total = 0
        for path, data in source_bytes.items():
            digest = source_digests[path]
            if (type(path) is not str or type(data) is not bytes
                    or type(digest) is not str or SHA.fullmatch(digest) is None
                    or not data or b"\x00" in data
                    or hashlib.sha256(data).hexdigest() != digest):
                return _refuse("invalid_pinned_public_snapshot")
            total += len(data)
            if total > MAX_PUBLIC_BYTES:
                return _refuse("invalid_pinned_public_snapshot")
        # This bridge does not read SQLite: only the caller can prove that the
        # supplied copied ledger and independent human reviews are complete.
        evidence = prepare(
            jobs, claims, job_roles, human_reviews, [], now=now,
            trusted_sqlite_copy=True, trusted_role_mapping=True,
            trusted_human_reviews=True, complete_ledger=True,
            trusted_grounded_candidates=True,
            job_tasks=job_tasks, trusted_task_mapping=True)
        if evidence["task_mapping_verified"] is not True:
            return _refuse("task_identity_ledger_unverified")
        seen = set(evidence["seen_dedupe"])
        attempted = evidence["attempted_task_ids"]
        tasks_by_id = {t["id"]: t for t in queue["tasks"]}
        if len(tasks_by_id) != len(queue["tasks"]):
            return _refuse("invalid_pinned_public_snapshot")
        candidates, provenance = [], {}
        # select() returns only the FIRST grounded task; use a temporary
        # in-memory seen set to enumerate distinct proposals. This is NOT a
        # job claim and does not mutate the authoritative private ledger.
        for _ in range(len(queue["tasks"])):
            found = select(
                queue, routing, commit=commit,
                source_bytes=source_bytes, source_digests=source_digests,
                trusted_pinned_snapshot=True, authoritative_ledger=True,
                seen_dedupe=seen, stop_present=False,
                approved_active_ids=approved_active_ids,
                trusted_owner_approval=trusted_owner_approval)
            if found["status"] == "no_eligible_grounded_task":
                break
            if found["status"] != "grounded_proposal_review_only":
                return _refuse("public_grounding_refused")
            item = found["candidate"]
            key = item["dedupe_key"]
            if key in seen:
                return _refuse("duplicate_public_grounding")
            seen.add(key)
            if item["task_id"] in attempted:
                continue
            task = tasks_by_id[item["task_id"]]
            priority = task.get("priority")
            if type(priority) is not int or not 1 <= priority <= 5:
                return _refuse("invalid_grounded_priority")
            candidates.append({
                "role": item["role"], "task_id": item["task_id"],
                "dedupe_key": key, "source_sha256": item["source_sha256"],
                "priority": priority})
            provenance[key] = (item["source_path"], item["pinned_commit"])
        if not candidates:
            return _refuse("no_unattempted_grounded_task")
        # Only original authenticated seen history is authoritative here;
        # temporary enumeration markers must NOT masquerade as past jobs.
        result = choose(
            candidates, evidence["outcomes"], now=now,
            seen_dedupe=evidence["seen_dedupe"],
            attempted_task_ids=attempted, trusted_task_mapping=True,
            trusted_candidates=True, trusted_outcomes=True,
            authoritative_ledger=True, stop_present=False,
            other_job_running=False, owner_opt_in=True)
        if result["status"] != "candidate_only_not_enqueued":
            response = _refuse(result["status"])
            if "coverage" in result:
                response["coverage"] = result["coverage"]
            return response
        selected = result["candidate"]
        if result.get("task_identity_ledger_verified") is not True:
            return _refuse("task_identity_ledger_unverified")
        path, pinned = provenance[selected["dedupe_key"]]
        return {
            "status": "review_only_not_dispatched",
            "candidate": {**selected, "source_path": path,
                          "pinned_commit": pinned, "review_required": True,
                          "model_use_authorized": False},
            "coverage": result["coverage"],
            "requires_fresh_atomic_sqlite_claim": True,
            "requires_independent_human_review": True,
            "requires_fresh_free_provider_and_quota_evidence": True,
            "model_calls": 0, "queue_writes": 0, "mac_execution": False,
        }
    except (BridgeError, GroundingError, CoverageError, KeyError,
            TypeError, ValueError, AttributeError, OverflowError):
        # Do not echo exception text: copied receipts may contain private
        # paths, prompts, or error messages.
        return _refuse("invalid_or_incomplete_evidence")
