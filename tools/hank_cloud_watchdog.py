#!/usr/bin/env python3
"""Hank: recurring read-only GitHub-hosted QA. No model, network or Mac execution."""
import argparse
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


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--summary-file", type=Path)
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
    print(json.dumps({"status": result["status"], "tasks": result["tasks"],
                      "errors": result["errors"], "stale": result["stale_claims"]}, sort_keys=True))
    return 0 if result["status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
