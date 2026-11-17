#!/usr/bin/env python3
"""Read-only inventory of GitHub Actions triggers, permissions and concurrency.

Uses only Python's standard library. No GitHub tokens or network needed.
This is a heuristic YAML surface audit, NOT a full workflow security validator.
"""
import argparse
import json
import re
from pathlib import Path

DISPATCH_PATHS = {
    "ghost-cloud-github-scheduler.yml",
    "ghost-cloud-scheduled-shift.yml",
    "start-cloud-workforce.yml",
    "cloud-gemini-workforce.yml",
    "ghost-cloud-operations.yml",
    "ghost-cloud-refill-batch.yml",
    "ghost-cloud.yml",
}
KEY_PATTERN = re.compile(r"^([A-Za-z_][\w-]*):\s*(?:#.*)?$")
CRON_PATTERN = re.compile(r"^\s*-\s*cron:\s*(.+?)\s*(?:#.*)?$")
SECTION_PATTERN = re.compile(r"^([A-Za-z_][\w-]*):(?:\s|$)")
KNOWN_EVENTS = {"push", "pull_request", "pull_request_target", "schedule",
                "workflow_dispatch", "workflow_call", "workflow_run", "repository_dispatch"}

def inspect(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    events = set()
    crons = []
    top_permissions = []
    concurrency = False
    section = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            match = SECTION_PATTERN.match(line)
            section = match.group(1) if match else None
            if section == "concurrency":
                concurrency = True
            if section == "on":
                # Support inline: on: [push, pull_request]
                inline = re.search(r"^on:\s*\[(.*?)\]", line)
                if inline:
                    events.update(x.strip().strip("'\"") for x in inline.group(1).split(",") if x.strip())
            continue
        if section == "on":
            match = re.match(r"^  ([\w-]+):(?:\s|$)", line)
            if match and match.group(1) in KNOWN_EVENTS:
                events.add(match.group(1))
            cron = CRON_PATTERN.match(line)
            if cron:
                crons.append(cron.group(1).strip().strip("'\""))
        elif section == "permissions":
            if re.match(r"^  [\w-]+:\s*\w+", line):
                top_permissions.append(line.strip())
    return {
        "file": path.name,
        "events": sorted(events),
        "cron": crons,
        "top_level_permissions": top_permissions,
        "has_top_level_concurrency": concurrency,
        "potential_dispatcher": path.name in DISPATCH_PATHS,
        "risk_flags": (["scheduled_dispatcher_requires_manual_review"]
                       if crons and path.name in DISPATCH_PATHS else []),
    }

def inventory(directory):
    if not directory.is_dir():
        raise ValueError(f"Workflow directory missing: {directory}")
    rows = [inspect(p) for p in sorted(directory.iterdir())
            if p.is_file() and p.suffix in (".yml", ".yaml")]
    return {
        "schema": "rovor.workflow-inventory.v1",
        "workflow_count": len(rows),
        "scheduled_workflows": [r["file"] for r in rows if r["cron"]],
        "schedule_count": sum(len(r["cron"]) for r in rows),
        "requires_review": [r["file"] for r in rows if r["risk_flags"]],
        "workflows": rows,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--output", type=Path, help="Write machine-readable inventory here")
    parser.add_argument("--fail-on-dispatch-cron", action="store_true",
                        help="Exit nonzero when a known dispatcher gains a cron")
    args = parser.parse_args()
    report = inventory(args.directory)
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.fail_on_dispatch_cron and report["requires_review"]:
        parser.exit(2, "Unsafe scheduled dispatcher(s): " +
                    ", ".join(report["requires_review"]) + "\n")

if __name__ == "__main__":
    main()
