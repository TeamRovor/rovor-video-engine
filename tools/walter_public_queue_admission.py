#!/usr/bin/env python3
"""Fail-closed pre-enqueue gate for the EXISTING OmniRoute public-task feeder.

PR #137 can propose a public_task for blocked/owned work, or fall back to a
generic catalogue. This source-only gate admits neither automatically. It
verifies an exact pinned task against the existing grounding/ownership rules
and an independently authenticated complete attempted-task ledger.

Call BEFORE enqueuing a NEW public_task, not to re-admit an already queued or
failed job. No SQLite, network, inference, scheduler, Mac access or writes.
Trust flags are caller attestations, not authentication performed here.
"""
import hashlib
import re

from walter_public_task_grounding import GroundingError, select

FORMS = frozenset(("plan", "checklist", "tests", "handoff"))
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
TASK_ID = re.compile(r"^[a-z][a-z0-9-]{2,119}$")
PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
MAX_TASKS = 500
MAX_SOURCES = 500
MAX_BYTES = 4000000


def _refuse(reason):
    return {"status": reason, "candidate": None, "model_calls": 0,
            "queue_writes": 0, "mac_execution": False}


def _valid_path(path):
    return (type(path) is str and PATH.fullmatch(path) is not None
            and all(p not in ("", ".", "..", ".git") and
                    not p.startswith(".env") for p in path.split("/")))


def _verified_sources(source_bytes, source_digests):
    if (type(source_bytes) is not dict or type(source_digests) is not dict
            or set(source_bytes) != set(source_digests)
            or len(source_bytes) > MAX_SOURCES):
        return False
    total = 0
    for path, data in source_bytes.items():
        if (not _valid_path(path) or type(data) is not bytes
                or not data or b"\x00" in data
                or type(source_digests[path]) is not str
                or SHA.fullmatch(source_digests[path]) is None
                or hashlib.sha256(data).hexdigest() != source_digests[path]):
            return False
        total += len(data)
        if total > MAX_BYTES:
            return False
    return True


def _scope_overlap(target, queue):
    """A ready task cannot silently use another unfinished owner's scope."""
    scopes = target.get("scopes")
    if not isinstance(scopes, list) or any(type(s) is not str for s in scopes):
        return True
    own = set(scopes)
    for other in queue["tasks"]:
        if other["id"] == target["id"] or other.get("status") == "done":
            continue
        other_scopes = other.get("scopes")
        if not isinstance(other_scopes, list) or any(type(s) is not str
                                                     for s in other_scopes):
            return True
        for a in own:
            for b in other_scopes:
                if a == b:
                    return True
                # Treat a directory scope as overlapping a nested file scope.
                if (not a.startswith("subsystem:") and
                        not b.startswith("subsystem:") and
                        (a.endswith("/") or b.endswith("/")) and
                        (a.startswith(b.rstrip("/") + "/") or
                         b.startswith(a.rstrip("/") + "/"))):
                    return True
    return False


def admit(payload, queue, routing, *, commit, source_bytes, source_digests,
          seen_dedupe, attempted_task_ids, claimed_role,
          trusted_pinned_snapshot=False, trusted_seen_ledger=False,
          trusted_task_ledger=False, complete_ledger=False,
          owner_opt_in=False, stop_present=True, other_job_running=True,
          approved_active_ids=(), trusted_owner_approval=False):
    """Return a public-only, inert seed candidate or a fixed refusal code.

    The caller must authenticate one immutable Git tree for queue, routing and
    sources, and a complete private job->task mapping including queued jobs.
    The proposed task MUST NOT already be in that ledger. A caller must still
    independently recheck STOP, verified free billing/quota and atomic claim
    immediately before any separately approved dispatch.
    """
    if stop_present is not False:
        return _refuse("stopped")
    if (owner_opt_in is not True or other_job_running is not False
            or trusted_pinned_snapshot is not True
            or trusted_seen_ledger is not True
            or trusted_task_ledger is not True
            or complete_ledger is not True):
        return _refuse("unverified_authority")
    if (type(commit) is not str or COMMIT.fullmatch(commit) is None
            or type(queue) is not dict or type(queue.get("tasks")) is not list
            or len(queue["tasks"]) > MAX_TASKS
            or type(routing) is not dict or not _verified_sources(
                source_bytes, source_digests)):
        return _refuse("pinned_snapshot_unverified")
    if (not isinstance(seen_dedupe, (set, frozenset))
            or len(seen_dedupe) > 100000
            or any(type(x) is not str or len(x) > 100 for x in seen_dedupe)
            or not isinstance(attempted_task_ids, (set, frozenset))
            or len(attempted_task_ids) > 100000
            or any(type(x) is not str or TASK_ID.fullmatch(x) is None
                   for x in attempted_task_ids)):
        return _refuse("task_history_unverified")
    if type(payload) is not dict or set(payload) != {"public_task"}:
        return _refuse("legacy_or_generic_packet_requires_review")
    public = payload["public_task"]
    if (type(public) is not dict or set(public) != {
                "id", "title", "acceptance", "commit", "form"}
            or type(public["id"]) is not str
            or TASK_ID.fullmatch(public["id"]) is None
            or type(public["form"]) is not str or public["form"] not in FORMS
            or type(public["title"]) is not str
            or type(public["acceptance"]) is not str
            or public["commit"] != commit):
        return _refuse("invalid_or_stale_public_payload")
    if public["id"] in attempted_task_ids:
        return _refuse("task_already_attempted_no_replay")
    if type(claimed_role) is not str:
        return _refuse("unverified_specialist_role")
    try:
        # Validate the paired queue and the entire pinned-source candidate
        # sequence through the already-reviewed source grounding gate.
        seen = set(seen_dedupe)
        selected = None
        for _ in range(len(queue["tasks"])):
            result = select(
                queue, routing, commit=commit,
                source_bytes=source_bytes, source_digests=source_digests,
                trusted_pinned_snapshot=True, authoritative_ledger=True,
                seen_dedupe=seen, stop_present=False,
                approved_active_ids=approved_active_ids,
                trusted_owner_approval=trusted_owner_approval)
            if result["status"] == "no_eligible_grounded_task":
                break
            if result["status"] != "grounded_proposal_review_only":
                return _refuse("source_grounding_refused")
            candidate = result["candidate"]
            if candidate["dedupe_key"] in seen:
                return _refuse("source_grounding_refused")
            if candidate["task_id"] == public["id"]:
                selected = candidate
                break
            seen.add(candidate["dedupe_key"])
        if selected is None:
            return _refuse("public_task_not_eligible")
        if (public["title"] != selected["title"]
                or public["acceptance"] != selected["acceptance"]):
            return _refuse("invalid_or_stale_public_payload")
        if selected["role"] != claimed_role:
            return _refuse("unverified_specialist_role")
        task = next(t for t in queue["tasks"] if t["id"] == public["id"])
        if _scope_overlap(task, queue):
            return _refuse("unfinished_scope_conflict")
        return {
            "status": "grounded_public_seed_review_only",
            "candidate": {
                "payload": {"public_task": dict(public)},
                "task_id": selected["task_id"],
                "role": selected["role"],
                "source_path": selected["source_path"],
                "source_sha256": selected["source_sha256"],
                "pinned_commit": selected["pinned_commit"],
                "grounded_dedupe_key": selected["dedupe_key"],
                "review_required": True,
                "model_use_authorized": False,
                "external_effects_allowed": False,
            },
            "requires_fresh_atomic_sqlite_claim": True,
            "requires_fresh_free_provider_and_quota_evidence": True,
            "requires_independent_human_review": True,
            "model_calls": 0, "queue_writes": 0, "mac_execution": False,
        }
    except (GroundingError, KeyError, ValueError, TypeError,
            AttributeError, OverflowError):
        # Never echo untrusted source, private ledger, or model text.
        return _refuse("invalid_or_incomplete_evidence")
