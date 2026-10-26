#!/usr/bin/env python3
"""Admit ONE source-grounded public research proposal for the existing worker.

Pure, read-only policy. Not a scheduler, SQLite adapter, model client, or a
permission to infer. The caller must authenticate a pinned public Git tree,
independently verify its file bytes and digests, and obtain the existing SQLite
seen-dedupe ledger. This function never trusts an LLM's own attestations.
"""
import hashlib
import json
import re

COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TASK_ID = re.compile(r"^[a-z][a-z0-9-]{2,119}$")
SOURCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
CODE = (".py", ".js", ".ts", ".lua", ".sh")
PUBLIC_CAPABILITIES = frozenset(("github-read", "github-write", "hosted-ci"))
ROLE_MARKERS = {
    "jane": ("fcp", "final-cut", "final_cut", "caption", "video-edit"),
    "jesse": ("moho", "viseme", "phoneme", "evan-engine", "animation", "speech"),
    "gale": ("blender", "3d"),
    "saul": ("marketing", "outreach", "sales", "social-media", "social_"),
    "mike": ("omniroute", "ghost_worker", "ghost-", "mac-", "mac_",
             "launchd", "open-interpreter", "interpreter", "supervisor"),
}


class GroundingError(ValueError):
    """Stable rejection reason; never includes source or draft text."""


def _deny(code):
    raise GroundingError(code)


def _path(value):
    return (type(value) is str and SOURCE.fullmatch(value) is not None
            and all(p not in ("", ".", "..") for p in value.split("/"))
            and not any(p.startswith(".env") or p == ".git" for p in value.split("/")))


def _role(scopes, source):
    # Ignore generic test/workflow scopes when deciding the specialist: a
    # regression for an OmniRoute bug belongs to Mike, not Hank by default.
    paths = [p.lower() for p in scopes if not p.startswith("subsystem:")]
    specific = [p for p in paths if not p.startswith(("tests/", ".github/workflows/"))]
    candidates = specific or paths
    hits = set()
    for path in candidates:
        for role, markers in ROLE_MARKERS.items():
            if any(m in path for m in markers):
                hits.add(role)
    # A marketing source in business/ belongs to Saul; general business ops
    # only falls back to Gus if no specific specialist was identified.
    if len(hits) != 1:
        if hits:
            return None
        if source.startswith("business/"):
            return "gus"
        if source.startswith("tests/") or "/qa" in source.lower():
            return "hank"
        return None
    return next(iter(hits))


def _source_for(task, source_bytes, source_digests):
    if (not isinstance(source_bytes, dict) or not isinstance(source_digests, dict)
            or set(source_bytes) != set(source_digests)):
        _deny("source_snapshot_unverified")
    scopes = task.get("scopes")
    if (not isinstance(scopes, list) or not scopes
            or any(type(s) is not str or not _path(s.replace("subsystem:", "subsystem-", 1))
                   for s in scopes)):
        return None
    # Exact file identity, never a directory or an inferred code path.
    eligible = sorted(s for s in scopes if _path(s) and s.endswith(CODE)
                      and s in source_bytes)
    eligible.sort(key=lambda s: (s.startswith(("tests/", ".github/")), s))
    for path in eligible:
        data = source_bytes[path]
        digest = source_digests[path]
        if (type(data) is not bytes or not 1 <= len(data) <= 19000
                or b"\x00" in data or type(digest) is not str
                or not SHA256.fullmatch(digest)):
            _deny("source_snapshot_unverified")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            _deny("source_snapshot_unverified")
        if hashlib.sha256(data).hexdigest() != digest:
            _deny("source_digest_mismatch")
        return path, digest
    return None


def select(queue, routing, *, commit, source_bytes, source_digests,
           trusted_pinned_snapshot=False, authoritative_ledger=False,
           seen_dedupe=None, stop_present=True, approved_active_ids=(),
           trusted_owner_approval=False):
    """Return one inert, deduplicated public task proposal or a safe status.

    Only trusted caller-supplied exact pinned Git tree content is admissible.
    Active work requires separately authenticated owner opt-in; blocked tasks,
    unmet dependencies and host-only tasks are never dispatched. No fallback
    to ungrounded generic topics or a guessed Mike role.
    """
    if stop_present:
        return {"status": "stopped", "candidate": None}
    if (trusted_pinned_snapshot is not True or type(commit) is not str
            or not COMMIT.fullmatch(commit)):
        return {"status": "pinned_snapshot_unverified", "candidate": None}
    if (authoritative_ledger is not True or not isinstance(seen_dedupe, (set, frozenset))
            or len(seen_dedupe) > 100000
            or any(type(x) is not str or len(x) > 100 for x in seen_dedupe)):
        return {"status": "ledger_unverified", "candidate": None}
    if (not isinstance(queue, dict) or queue.get("version") != 1
            or not isinstance(queue.get("tasks"), list)
            or not isinstance(routing, dict) or routing.get("version") != 1
            or not isinstance(routing.get("tasks"), dict)):
        _deny("invalid_paired_queue")
    tasks = queue["tasks"]
    if (len(tasks) > 10000 or any(not isinstance(t, dict)
            or type(t.get("id")) is not str or not TASK_ID.fullmatch(t["id"])
            for t in tasks)):
        _deny("invalid_paired_queue")
    by_id = {t["id"]: t for t in tasks}
    if (len(by_id) != len(tasks) or set(by_id) != set(routing["tasks"])):
        _deny("invalid_paired_queue")
    if (not isinstance(approved_active_ids, (tuple, list, set, frozenset))
            or any(type(i) is not str or i not in by_id for i in approved_active_ids)):
        _deny("invalid_owner_approval")
    approved = set(approved_active_ids) if trusted_owner_approval is True else set()
    if approved_active_ids and trusted_owner_approval is not True:
        return {"status": "owner_approval_unverified", "candidate": None}
    for task in sorted(tasks, key=lambda t: (
            t.get("priority") if type(t.get("priority")) is int
            and t["priority"] > 0 else 999999, t["id"])):
        status = task.get("status")
        if status == "ready":
            if task.get("owner") is not None:
                continue
        elif status == "active":
            if (task["id"] not in approved or not isinstance(task.get("owner"), str)
                    or not task["owner"].strip()):
                continue
        else:
            continue
        deps = task.get("depends_on", [])
        if (not isinstance(deps, list) or any(type(d) is not str or d not in by_id
                or by_id[d].get("status") != "done" for d in deps)):
            continue
        policy = routing["tasks"].get(task["id"])
        if (not isinstance(policy, dict) or not isinstance(policy.get("lane"), str)
                or not isinstance(policy.get("requires"), list)
                or any(type(x) is not str or x not in PUBLIC_CAPABILITIES
                       for x in policy["requires"])):
            continue
        title, acceptance = task.get("title"), task.get("acceptance")
        if (type(title) is not str or not 15 <= len(title) <= 250
                or type(acceptance) is not str or not 25 <= len(acceptance) <= 1600
                or "\x00" in title + acceptance):
            continue
        source = _source_for(task, source_bytes, source_digests)
        if source is None:
            continue
        path, digest = source
        role = _role(task["scopes"], path)
        if role is None:
            continue
        identity = {"task_id": task["id"], "role": role,
                    "source_path": path, "source_sha256": digest,
                    "title": title, "acceptance": acceptance}
        dedupe = "grounded-public-v1-" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if dedupe in seen_dedupe:
            continue
        return {"status": "grounded_proposal_review_only", "candidate": {
            **identity, "pinned_commit": commit, "dedupe_key": dedupe,
            "review_required": True, "model_use_authorized": False,
            "external_effects_allowed": False}}
    return {"status": "no_eligible_grounded_task", "candidate": None}
