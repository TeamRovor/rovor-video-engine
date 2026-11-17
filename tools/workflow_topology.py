#!/usr/bin/env python3
"""Read-only GitHub Actions inventory and fail-closed legacy-scheduler guard.

Uses only Python's standard library. Never evaluates a workflow, reads secrets,
starts a job, or changes runtime configuration.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

WORKFLOW_GLOB = ("*.yml", "*.yaml")
LEGACY_SHIFT_SCRIPT = "tools/ghost_cloud_hosted_shift.py"
LEGACY_SCHEDULER = "ghost-cloud-github-scheduler.yml"


def events_in(text: str) -> list[str]:
    """Read the top-level YAML 'on' key without treating YAML 1.1 'on' as boolean.

    This is a small GitHub event-key scanner, not a general YAML parser.
    Unknown syntax is reported, never interpreted as authorization to run.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(?:on|'on'|\"on\"):\s*(.*)$", line)
        if not match:
            continue
        tail = match.group(1).split("#", 1)[0].strip()
        if tail:
            if tail.startswith("[") and tail.endswith("]"):
                return sorted(set(x.strip().strip("'\"") for x in tail[1:-1].split(",") if x.strip()))
            if re.fullmatch(r"[\w-]+", tail):
                return [tail]
            return ["<unparsed-inline-on>"]
        events = set()
        for child in lines[index + 1:]:
            if child.strip() and not child[0].isspace() and not child.lstrip().startswith("#"):
                break
            event = re.match(r"^  ([\w-]+):(?:\s|$)", child)
            if event:
                events.add(event.group(1))
        return sorted(events)
    return []


def job_count(text: str) -> int:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line == "jobs:"), None)
    if start is None:
        return 0
    count = 0
    for line in lines[start + 1:]:
        if line.strip() and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        if re.match(r"^  [\w-]+:\s*(?:#.*)?$", line):
            count += 1
    return count


def category(name: str) -> str:
    if name.startswith(("ghost-cloud", "cloud-gemini", "start-cloud")):
        return "Cloud workforce"
    if name.startswith(("omniroute", "connect-google", "verify-gemini")):
        return "Provider routing"
    if "hud" in name or "dashboard" in name or "command-center" in name:
        return "HUD and telemetry"
    if name.startswith(("moho", "rovor-moho", "speech", "painting")):
        return "Creative / Moho"
    if name.startswith(("walter", "rovor-ai", "rovor-autonomous", "hank")):
        return "Worker orchestration"
    return "Repository / delivery"


def scan(repo_root: Path) -> dict:
    directory = repo_root / ".github" / "workflows"
    files = sorted({p for pattern in WORKFLOW_GLOB for p in directory.glob(pattern)})
    issues = []
    warnings = []
    entries = []
    if not files:
        return {"workflows": [], "issues": ["No GitHub Actions workflow files were found"], "warnings": [], "totals": {}}

    for path in files:
        text = path.read_text(encoding="utf-8")
        events = events_in(text)
        scheduled = "schedule" in events
        permissions = bool(re.search(r"^permissions:", text, re.MULTILINE))
        concurrency = bool(re.search(r"^\s*concurrency:", text, re.MULTILINE))
        source = path.name
        jobs = job_count(text)
        entries.append({
            "name": source,
            "category": category(source),
            "events": events,
            "jobs": jobs,
            "concurrency": concurrency,
            "permissions": permissions,
        })

        # Critical ownership boundary: the existing Cloudflare Worker is the
        # only production cloud-shift timer. The old GitHub->Site 403 route may
        # be invoked for a deliberate diagnostic, but never on a cron.
        if scheduled and source == LEGACY_SCHEDULER:
            issues.append(f"{source}: legacy Site scheduler must remain manual-only")
        if scheduled and LEGACY_SHIFT_SCRIPT in text:
            issues.append(f"{source}: cron must not invoke retired Site shift client")
        if "pull_request_target" in events:
            warnings.append(f"{source}: review privileged pull_request_target event")
        if not events:
            warnings.append(f"{source}: no parseable trigger; review YAML syntax")
        if not permissions:
            warnings.append(f"{source}: no explicit workflow-level permissions")
        if scheduled and not concurrency:
            warnings.append(f"{source}: scheduled workflow lacks concurrency guard")

    return {
        "workflows": entries,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "totals": {
            "workflows": len(entries),
            "jobs": sum(e["jobs"] for e in entries),
            "scheduled": sum("schedule" in e["events"] for e in entries),
            "manual": sum("workflow_dispatch" in e["events"] for e in entries),
            "by_category": dict(sorted(Counter(e["category"] for e in entries).items())),
        },
    }


def markdown(report: dict) -> str:
    totals = report["totals"]
    rows = [
        "# ROVOR GitHub Actions topology",
        "",
        "Read-only source inventory; **not** evidence of live model calls, available quotas, or production readiness.",
        "",
        f"- Workflow files: **{totals.get('workflows', 0)}**",
        f"- Declared jobs: **{totals.get('jobs', 0)}**",
        f"- GitHub-cron workflows: **{totals.get('scheduled', 0)}** (not necessarily cloud-shift schedulers)",
        f"- Manual-entry workflows: **{totals.get('manual', 0)}**",
        f"- Critical topology violations: **{len(report['issues'])}**",
        "",
        "Production cloud-shift scheduling belongs to the existing native Cloudflare Worker, not GitHub Actions. A GitHub cron for reporting or PR proposals does not imply inference.",
        "",
        "## Workflow inventory",
        "",
        "| Group | Workflow | Trigger(s) | Jobs | Concurrency |",
        "| --- | --- | --- | ---: | :---: |",
    ]
    for e in sorted(report["workflows"], key=lambda x: (x["category"], x["name"])):
        rows.append(f"| {e['category']} | \`{e['name']}\` | {', '.join(e['events']) or 'UNKNOWN'} | {e['jobs']} | {'yes' if e['concurrency'] else 'no'} |")
    rows.extend(["", "## Critical findings", ""])
    rows.extend(f"- {x}" for x in report["issues"]) if report["issues"] else rows.append("- None detected")
    rows.extend(["", "## Review recommendations (non-blocking)", ""])
    rows.extend(f"- {x}" for x in report["warnings"]) if report["warnings"] else rows.append("- None")
    rows.append("")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--check", action="store_true", help="fail only on critical topology violations")
    args = parser.parse_args()
    report = scan(args.root)
    print(json.dumps(report, indent=2) if args.format == "json" else markdown(report))
    return 1 if args.check and report["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
