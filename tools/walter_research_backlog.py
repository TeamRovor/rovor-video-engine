#!/usr/bin/env python3
"""Walter's bounded research release preview. Never invokes models or edits queue."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("coordination/walter-approved-research-backlog.json")
ROLES = frozenset(("mike", "jane", "jesse", "gale", "gus", "saul", "hank"))
PUBLIC_SOURCES = frozenset((
    "AGENTS.md", "WORK.md", "ROVOR-AI-PLAN.md",
    "architecture/HYBRID-24-7-GHOST-WORKFORCE.md",
    "coordination/ghost-provider-policy.json",
    "coordination/ghost-role-bootstrap.json",
    "integrations/open-interpreter/HANK-CLOUD-WATCHDOG.md",
))
JOB_ID = re.compile(r"^walter-public-v1-[a-z0-9-]{3,64}$")
EXPECTED_SAFETY = {
    "max_jobs_per_tick": 1,
    "existing_omniroute_max_claims_per_rolling_24h": 5,
    "never_replay_seen_dedupe": True,
    "auto_generate_followups": False,
    "requires_live_free_model_verification": True,
    "requires_separate_owner_model_use_opt_in": True,
    "client_private_content_allowed": False,
    "paid_fallback_allowed": False,
    "external_effects_allowed": False,
    "requires_STOP_absent": True,
}


def validated(root):
    """Validate one bounded release against immutable public source files."""
    root = Path(root).resolve(strict=True)
    path = root / MANIFEST
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise ValueError("unsafe_manifest")
    if path.stat().st_size > 32000:
        raise ValueError("manifest_too_large")
    with path.open(encoding="utf-8") as stream:
        doc = json.load(stream)
    if (not isinstance(doc, dict) or
            set(doc) != {"schema_version", "release", "visibility", "status", "policy", "jobs"} or
            doc["schema_version"] != 1 or
            doc["release"] != "walter-public-research-v1" or
            doc["visibility"] != "public-repository-metadata-only" or
            doc["status"] != "staged_not_integrated" or
            not isinstance(doc["policy"], dict) or
            set(doc["policy"]) != set(EXPECTED_SAFETY) or
            any(type(doc["policy"][key]) is not type(value) or
                doc["policy"][key] != value
                for key, value in EXPECTED_SAFETY.items())):
        raise ValueError("unsafe_release_policy")
    jobs = doc["jobs"]
    if not isinstance(jobs, list) or len(jobs) != 14:
        raise ValueError("unexpected_backlog_size")
    seen = set()
    roles = Counter()
    required = {"id", "role", "stage", "approved_for_proposal", "dedupe_key",
                "sources", "task", "deliverable", "acceptance",
                "external_effects_allowed", "model_inference_authorized_by_manifest"}
    for index, job in enumerate(jobs):
        if not isinstance(job, dict) or set(job) != required:
            raise ValueError("invalid_job_shape")
        role = job["role"]
        jid = job["id"]
        if (type(jid) is not str or not JOB_ID.fullmatch(jid) or jid in seen or
                job["dedupe_key"] != jid or role not in ROLES or
                job["stage"] != (1 if index < 7 else 2) or
                role in [x["role"] for x in jobs[(index // 7) * 7:index]]):
            raise ValueError("duplicate_or_unapproved_job")
        seen.add(jid)
        roles[role] += 1
        if (job["approved_for_proposal"] is not True or
                job["external_effects_allowed"] is not False or
                job["model_inference_authorized_by_manifest"] is not False or
                not isinstance(job["task"], str) or
                not 30 <= len(job["task"]) <= 700 or
                not isinstance(job["deliverable"], str) or
                not 20 <= len(job["deliverable"]) <= 400 or
                not isinstance(job["acceptance"], list) or
                len(job["acceptance"]) != 3 or
                any(not isinstance(x, str) or len(x) > 200 for x in job["acceptance"])):
            raise ValueError("job_safety_violation")
        sources = job["sources"]
        if (not isinstance(sources, list) or not 1 <= len(sources) <= 3 or
                len(sources) != len(set(sources)) or
                any(type(source) is not str or source not in PUBLIC_SOURCES
                    for source in sources)):
            raise ValueError("unapproved_source")
        size = 0
        for rel in sources:
            file = root / rel
            part = root
            for segment in Path(rel).parts:
                part = part / segment
                if part.is_symlink():
                    raise ValueError("unavailable_or_redirected_public_source")
            if not file.is_file():
                raise ValueError("unavailable_or_redirected_public_source")
            data = file.read_bytes()
            if len(data) > 19000:
                raise ValueError("oversized_public_source")
            size += len(data.decode("utf-8"))
        if size > 28000:
            raise ValueError("combined_input_exceeds_existing_runner_limit")
    if dict(roles) != {role: 2 for role in ROLES}:
        raise ValueError("incomplete_role_coverage")
    return doc


def select_next(release, *, seen_dedupe=None, authoritative_ledger=False,
                stop_present=True, separate_model_approval=False,
                verified_free_route=False, remaining_claims=0):
    """Read-only candidate; does NOT enqueue, invoke inference or change Mac state.

    Caller must obtain seen_dedupe from the existing SQLite ledger, not create
    a separate shadow queue or retry a terminal receipt after an uncertain call.
    """
    if stop_present:
        return {"status": "stopped", "candidate": None}
    if not authoritative_ledger or seen_dedupe is None:
        return {"status": "ledger_unverified", "candidate": None}
    if not separate_model_approval:
        return {"status": "model_use_not_authorized", "candidate": None}
    if not verified_free_route:
        return {"status": "free_route_unverified", "candidate": None}
    if type(remaining_claims) is not int or remaining_claims < 1 or remaining_claims > 5:
        return {"status": "quota_unavailable", "candidate": None}
    if not isinstance(seen_dedupe, (set, frozenset)) or any(
            not isinstance(key, str) for key in seen_dedupe):
        return {"status": "ledger_unverified", "candidate": None}
    for job in release["jobs"]:
        if job["dedupe_key"] not in seen_dedupe:
            return {"status": "candidate_only_not_enqueued",
                    "candidate": {"id": job["id"], "role": job["role"],
                                  "stage": job["stage"],
                                  "dedupe_key": job["dedupe_key"]}}
    return {"status": "exhausted_review_required", "candidate": None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        release = validated(args.root)
        # Default path is validation only. Live selection requires existing
        # SQLite ledger + real host free route and opt-in, never CLI guesses.
        print(json.dumps({"status": "public_backlog_validated_not_deployed",
                          "staged_jobs": len(release["jobs"]),
                          "roles": sorted(ROLES),
                          "model_calls": 0, "queue_writes": 0,
                          "automatic_model_use": False}, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, UnicodeError, KeyError) as exc:
        # Prevent filesystem paths/private source strings reaching public logs.
        print(json.dumps({"status": "blocked",
                          "error_class": type(exc).__name__,
                          "model_calls": 0, "queue_writes": 0}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
