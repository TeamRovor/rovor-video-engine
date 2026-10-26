#!/usr/bin/env python3
"""Hank: recurring read-only GitHub-hosted QA. No model, network or Mac execution."""
import argparse
import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"Mike", "Jane", "Jesse", "Gale", "Gus", "Saul", "Hank"}
EVIDENCE = ("commit", "platform", "check", "result", "reference")
STATUSES = ("active", "blocked", "ready", "done")
RECEIPT_INPUTS = ("tasks.json", "work-routing.json", "ghost-role-bootstrap.json",
                  "ghost-provider-policy.json")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_RUN_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
_CODE = re.compile(r"[a-z][a-z_]{2,63}\Z")


def loaded(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def audit(tasks, routes, roster, policy, now=None):
    now = now or datetime.now(timezone.utc)
    problems, warnings, counts = set(), set(), Counter()
    items = tasks.get("tasks", [])
    route = routes.get("tasks", {})
    if not isinstance(items, list) or not isinstance(route, dict):
        return {"status": "needs_review", "errors": ["invalid_task_structure"],
                "warnings": [], "counts": {}, "tasks": 0, "stale_claims": 0}
    ids = []
    stale = 0
    for t in items:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str):
            problems.add("invalid_task_structure")
            continue
        ids.append(t["id"])
        state = t.get("status")
        if state not in STATUSES:
            problems.add("invalid_task_status")
            continue
        counts[state] += 1
        if state in ("active", "blocked"):
            if not t.get("owner") or not t.get("next_update"):
                problems.add("claim_missing_owner_or_handoff")
            try:
                changed = datetime.fromisoformat(t["updated_at"].replace("Z", "+00:00"))
                if changed.tzinfo and (now - changed.astimezone(timezone.utc)).total_seconds() > 72 * 3600:
                    stale += 1
            except (KeyError, TypeError, ValueError):
                problems.add("claim_missing_timestamp")
        if state == "done":
            ev = t.get("evidence")
            if not isinstance(ev, list) or not ev or any(
                not isinstance(e, dict) or any(
                    not isinstance(e.get(k), str) or not e[k].strip() for k in EVIDENCE
                ) for e in ev
            ):
                problems.add("completed_task_evidence_invalid")
        deps = t.get("depends_on", [])
        if not isinstance(deps, list):
            problems.add("invalid_dependencies")
        elif any(not isinstance(d, str) or d == t["id"] for d in deps):
            problems.add("invalid_dependencies")
    allids = set(ids)
    if len(ids) != len(allids):
        problems.add("duplicate_task_ids")
    if set(route) != allids:
        problems.add("routing_missing_or_extra")
    for t in items:
        if isinstance(t, dict) and isinstance(t.get("depends_on"), list):
            if any(d not in allids for d in t["depends_on"]):
                problems.add("unknown_dependency")
    names = [r.get("id", "").title() for r in roster.get("roles", [])]
    pnames = [r.get("name") for r in policy.get("employees", [])]
    if (set(names) != ROLES or len(names) != 7 or
            set(pnames) != ROLES or len(pnames) != 7 or
            policy.get("supervisor", {}).get("employee") != "Walter"):
        problems.add("employee_roster_mismatch")
    safety = policy.get("safety", {})
    if (safety.get("default_paid_use_allowed") is not False or
            safety.get("legacy_failed_receipts_never_requeued") is not True or
            safety.get("stop_honored_on_every_dispatch") is not True or
            safety.get("existing_omniroute_rolling_24h_claim_cap") != 5 or
            policy.get("control_plane", {}).get("duplicate_scheduler_allowed") is not False):
        problems.add("zero_spend_stop_or_scheduler_policy_changed")
    if stale:
        warnings.add("stale_claims_need_owner_review")
    return {"status": "needs_review" if problems else "healthy",
            "errors": sorted(problems), "warnings": sorted(warnings),
            "counts": dict(sorted(counts.items())), "tasks": len(items),
            "stale_claims": stale}


def summary(report, sha):
    lines = ["## Hank — Unattended ROVOR QA",
             "", "**" + report["status"].upper() + "** — GitHub-hosted, read-only, no AI or Mac access.",
             "", "- Revision: " + str(sha)[:12],
             "- Tasks inspected: " + str(report["tasks"]),
             "- Stale owner claims (>72h): " + str(report["stale_claims"]),
             "- Task statuses: " + ", ".join(
                 k + "=" + str(v) for k, v in report["counts"].items()),
             "", "### Results"]
    lines += ["- " + x for x in report["errors"] or ["Core invariants passed"]]
    lines += ["- Warning: " + x for x in report["warnings"]]
    lines += ["", "No private content, API credentials, or local file paths were accessed.",
              "A push run does not verify a future cron wake-up."]
    return "\n".join(lines) + "\n"



def cloud_receipt(report, coordination_root, *, commit, run_id, attempt, observed_at):
    """Content-free evidence for ONE GitHub-hosted Hank audit, not model inference.

    Only a GitHub Actions artifact attached to its actual run authenticates
    provenance; these caller-supplied fields are not cryptographic attestation.
    No task text, owner, client data, secrets or local paths enter this receipt.
    """
    if (not isinstance(commit, str) or not _HEX40.fullmatch(commit)
            or not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id)
            or type(attempt) is not int or not 1 <= attempt <= 1000
            or not isinstance(observed_at, datetime) or observed_at.tzinfo is None
            or observed_at.utcoffset().total_seconds() != 0):
        raise ValueError("receipt_provenance_invalid")
    if not isinstance(report, dict) or report.get("status") not in ("healthy", "needs_review"):
        raise ValueError("receipt_report_invalid")
    counts = report.get("counts")
    if (not isinstance(counts, dict) or any(
            key not in STATUSES or type(value) is not int or not 0 <= value <= 1000000
            for key, value in counts.items())):
        raise ValueError("receipt_report_invalid")
    for field in ("tasks", "stale_claims"):
        if type(report.get(field)) is not int or not 0 <= report[field] <= 1000000:
            raise ValueError("receipt_report_invalid")
    for field in ("errors", "warnings"):
        values = report.get(field)
        if (not isinstance(values, list) or len(values) > 24
                or any(not isinstance(value, str) or not _CODE.fullmatch(value)
                       for value in values)):
            raise ValueError("receipt_report_invalid")
    if report["status"] == "healthy" and report["errors"]:
        raise ValueError("receipt_report_invalid")
    root = Path(coordination_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("receipt_sources_invalid")
    digests = {}
    for name in RECEIPT_INPUTS:
        path = root / name
        if path.is_symlink():
            raise ValueError("receipt_sources_invalid")
        try:
            with path.open("rb") as handle:
                raw = handle.read(5000001)
        except OSError:
            raw = None
        if raw is not None and len(raw) > 5000000:
            raise ValueError("receipt_sources_invalid")
        digests[name] = hashlib.sha256(raw).hexdigest() if raw is not None else None
    if any(value is None for value in digests.values()) and report["status"] == "healthy":
        raise ValueError("receipt_sources_invalid")
    result = {
        "schema_version": 1,
        "employee": "Hank",
        "execution_source": "github_actions",
        "evidence_kind": "public_queue_policy_audit",
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "commit_sha": commit,
        "github_run_id": run_id,
        "github_run_attempt": attempt,
        "status": report["status"],
        "tasks_inspected": report["tasks"],
        "task_status_counts": dict(sorted(counts.items())),
        "stale_claims": report["stale_claims"],
        "errors": sorted(report["errors"]),
        "warnings": sorted(report["warnings"]),
        "public_input_sha256": digests,
        "human_review": "not_recorded",
        "model": None,
        "tokens": None,
        "mac_runtime_verified": False,
        "omniroute_inference_verified": False,
    }
    if len(json.dumps(result, sort_keys=True).encode("utf-8")) > 4096:
        raise ValueError("receipt_too_large")
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--summary-file", type=Path)
    p.add_argument("--receipt-file", type=Path,
                   help="GitHub Actions artifact path (no model or private data)")
    args = p.parse_args(argv)
    root = args.root / "coordination"
    try:
        result = audit(
            loaded(root / "tasks.json"),
            loaded(root / "work-routing.json"),
            loaded(root / "ghost-role-bootstrap.json"),
            loaded(root / "ghost-provider-policy.json"))
    except (OSError, ValueError, TypeError, KeyError):
        result = {"status": "needs_review", "errors": ["source_unavailable"],
                  "warnings": [], "counts": {}, "tasks": 0, "stale_claims": 0}
    if args.summary_file:
        with args.summary_file.open("a", encoding="utf-8") as handle:
            handle.write(summary(result, os.environ.get("GITHUB_SHA", "local")))
    if args.receipt_file:
        try:
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("receipt_provenance_invalid")
            evidence = cloud_receipt(
                result, root, commit=os.environ.get("GITHUB_SHA"),
                run_id=os.environ.get("GITHUB_RUN_ID"),
                attempt=int(os.environ.get("GITHUB_RUN_ATTEMPT", "0")),
                observed_at=datetime.now(timezone.utc))
            args.receipt_file.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except (ValueError, OSError, TypeError):
            print(json.dumps({"status": "needs_review",
                              "errors": ["receipt_provenance_or_source_invalid"]}),
                  file=sys.stderr)
            return 1
    print(json.dumps({"status": result["status"], "tasks": result["tasks"],
                      "errors": result["errors"], "stale": result["stale_claims"]}, sort_keys=True))
    return 0 if result["status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
