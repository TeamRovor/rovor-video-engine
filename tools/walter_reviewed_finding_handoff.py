#!/usr/bin/env python3
"""Turn a *separately human-reviewed* public research finding into an inert code handoff.

This is NOT a Mac worker, model output approver, scheduler, queue writer or
code executor. The caller must independently authenticate the human review,
source digests, repository snapshot and shared task queue. A model cannot
authorize itself by supplying a dictionary. No raw private draft is returned.
"""
import hashlib
import json
import re

from walter_source_citation_gate import CitationError, verify as verify_citation

ROLES = frozenset(("mike", "jane", "jesse", "gale", "gus", "saul", "hank"))
KEY = re.compile(r"^[a-z][a-z0-9-]{7,79}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
CODE_EXTENSIONS = (".py", ".js", ".ts", ".lua", ".sh")
CHANGE_TYPES = frozenset(("bugfix", "test", "reliability", "integration"))
GENERIC = (
    "tbd", "todo", "make better", "improve efficiency", "best practices",
    "research more", "explore options", "to be determined",
    "general improvements", "improve the code", "future research",
)
FIELDS = frozenset((
    "role", "finding_key", "change_type", "source_path", "source_line_start",
    "source_line_end", "source_sha256", "target_path", "target_sha256",
    "test_path", "subsystem", "problem", "change", "acceptance",
))


class HandoffError(ValueError):
    """A stable, content-free rejection code."""


def _fail(code):
    raise HandoffError(code)


def _path(value):
    return (type(value) is str and PATH.fullmatch(value) is not None
            and all(part not in ("", ".", "..") for part in value.split("/")))


def _digest(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _specific(value, minimum):
    if type(value) is not str or not minimum <= len(value) <= 700:
        return False
    normalized = " ".join(value.lower().split())
    if any(phrase in normalized for phrase in GENERIC):
        return False
    words = re.findall(r"[A-Za-z0-9_]+", value)
    return len(words) >= 8 and len(set(w.lower() for w in words)) >= 6


def _queue_conflict(tasks, task_id, scopes):
    if not isinstance(tasks, list):
        _fail("queue_snapshot_unverified")
    seen = set()
    for task in tasks:
        if (not isinstance(task, dict) or type(task.get("id")) is not str
                or task["id"] in seen
                or task.get("status") not in ("active", "blocked", "ready", "done")
                or not isinstance(task.get("scopes"), list)
                or any(type(s) is not str for s in task["scopes"])):
            _fail("queue_snapshot_unverified")
        seen.add(task["id"])
        if task["id"] == task_id:
            _fail("finding_already_recorded")
        if task["status"] != "done" and scopes.intersection(task["scopes"]):
            _fail("existing_task_scope_overlap")


def propose(finding, *, review_receipt, trusted_human_review=False,
            public_sources=None, request_source_sha256=None,
            repo_file_sha256=None, existing_tasks=None,
            trusted_queue_snapshot=False):
    """Return an inert, non-publishing task candidate or raise a fixed code.

    All input maps and flags must come from independent trusted callers, never
    the model draft itself. The citation check proves source-byte/line binding,
    not semantic truth. No automatic claim or code change is authorized.
    """
    if trusted_human_review is not True:
        _fail("independent_human_review_required")
    if trusted_queue_snapshot is not True:
        _fail("authoritative_queue_required")
    if not isinstance(finding, dict) or set(finding) != FIELDS:
        _fail("finding_schema_invalid")
    role = finding["role"]
    key = finding["finding_key"]
    if (type(role) is not str or role not in ROLES
            or type(key) is not str or KEY.fullmatch(key) is None
            or finding["change_type"] not in CHANGE_TYPES):
        _fail("finding_identity_invalid")
    for field in ("problem", "change", "acceptance"):
        if not _specific(finding[field], 55 if field != "acceptance" else 45):
            _fail("non_actionable_finding")
    if len({finding["problem"], finding["change"], finding["acceptance"]}) != 3:
        _fail("non_actionable_finding")
    source = finding["source_path"]
    target = finding["target_path"]
    test = finding["test_path"]
    subsystem = finding["subsystem"]
    if (not all(_path(p) for p in (source, target, test))
            or not target.startswith(("tools/", "evan-engine/", "integrations/"))
            or not target.endswith(CODE_EXTENSIONS)
            or not test.startswith("tests/test_") or not test.endswith(".py")
            or type(subsystem) is not str or not subsystem.startswith("subsystem:")
            or KEY.fullmatch(subsystem[len("subsystem:"):]) is None):
        _fail("unsafe_or_unscoped_target")
    if (not _digest(finding["source_sha256"])
            or not _digest(finding["target_sha256"])
            or not isinstance(repo_file_sha256, dict)
            or repo_file_sha256.get(target) != finding["target_sha256"]):
        _fail("target_revision_unverified")
    if (not isinstance(public_sources, dict)
            or not isinstance(request_source_sha256, dict)
            or source not in public_sources
            or request_source_sha256.get(source) != finding["source_sha256"]):
        _fail("source_snapshot_unverified")
    start = finding["source_line_start"]
    end = finding["source_line_end"]
    if (type(start) is not int or type(end) is not int
            or start < 1 or end < start or end - start >= 12):
        _fail("source_lines_invalid")
    try:
        proof = verify_citation(
            "[[source:{}#L{}-L{}]]".format(source, start, end),
            {source: public_sources[source]},
            {source: request_source_sha256[source]},
        )
    except (CitationError, TypeError, UnicodeError, ValueError):
        _fail("source_citation_unverified")
    if proof.get("reference_count") != 1:
        _fail("source_citation_unverified")
    if (not isinstance(review_receipt, dict)
            or set(review_receipt) != {
                "job_id", "status", "finding_key", "source_sha256"}
            or type(review_receipt["job_id"]) is not str
            or not 8 <= len(review_receipt["job_id"]) <= 100
            or review_receipt["status"] != "human_approved"
            or review_receipt["finding_key"] != key
            or review_receipt["source_sha256"] != finding["source_sha256"]):
        _fail("review_receipt_unverified")
    # Stable across unrelated commits or reworded draft text: no replay by
    # changing only the source digest, problem paragraph or model provider.
    task_id = "walter-finding-" + hashlib.sha256(
        (role + "|" + target + "|" + key).encode("utf-8")
    ).hexdigest()[:20]
    _queue_conflict(existing_tasks, task_id, {target, test, subsystem})
    details_hash = hashlib.sha256(json.dumps({
        "problem": finding["problem"], "change": finding["change"],
        "acceptance": finding["acceptance"],
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "status": "reviewed_candidate_requires_separate_claim",
        "candidate": {
            "id": task_id, "role": role, "finding_key": key,
            "change_type": finding["change_type"],
            "target_path": target, "target_sha256": finding["target_sha256"],
            "test_path": test, "subsystem": subsystem,
            "source_reference": {
                "path": source, "start_line": start, "end_line": end,
                "source_sha256": finding["source_sha256"],
            },
            "private_review_details_sha256": details_hash,
        },
        "human_review_attested_not_authenticated_here": True,
        "semantic_truth_independently_verified_here": False,
        "requires_fresh_atomic_queue_claim": True,
        "automatic_approval_or_publication": False,
        "model_calls": 0, "queue_writes": 0, "mac_execution": False,
    }
