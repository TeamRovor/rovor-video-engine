#!/usr/bin/env python3
"""Inventory GitHub Actions wiring without executing workflows or reading secrets.

This is a dependency-free, syntax-level inventory rather than a general YAML
validator. It reports observable triggers and permissions, never runtime health.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r"^([A-Za-z_][\w-]*|'[\w-]+'|\"[\w-]+\"):\s*(.*)$")


def sections(lines, indent=0):
    """Return (key, scalar, body) for mapping entries at one indentation level."""
    result = []
    pattern = re.compile(r"^" + " " * indent + KEY.pattern[1:])
    for line in lines:
        match = pattern.match(line)
        if match:
            result.append((match.group(1).strip("'\""), match.group(2).strip(), []))
        elif result:
            result[-1][2].append(line)
    return {key: (scalar, body) for key, scalar, body in result}


def mapping(body, indent):
    return {key: value for key, (value, _) in sections(body, indent).items()}


def events_from(on_scalar, on_body):
    events = list(sections(on_body, 2))
    if on_scalar.startswith("[") and on_scalar.endswith("]"):
        events += [x.strip().strip("'\"") for x in on_scalar[1:-1].split(",") if x.strip()]
    elif on_scalar and not on_scalar.startswith("#") and on_scalar not in ("{}", "null"):
        events.append(on_scalar.split("#", 1)[0].strip().strip("'\""))
    return sorted(set(events))


def read_workflow(path, root):
    data = path.read_text(encoding="utf-8")
    lines = data.splitlines()
    top = sections(lines)
    on_scalar, on_body = top.get("on", ("", []))
    events = events_from(on_scalar, on_body)
    cron_lines = []
    if "schedule" in events:
        schedule = sections(on_body, 2).get("schedule", ("", []))[1]
        for line in schedule:
            match = re.match(r"^\s+- cron:\s*(.+?)\s*(?:#.*)?$", line)
            if match:
                cron_lines.append(match.group(1).strip("'\""))
    global_permissions = top.get("permissions", ("unspecified", []))
    permission_map = mapping(global_permissions[1], 2)
    if not permission_map and global_permissions[0] != "unspecified":
        permission_map = {"_scalar": global_permissions[0]}
    conc_scalar, conc_body = top.get("concurrency", ("", []))
    global_group = mapping(conc_body, 2).get("group", conc_scalar) or None
    jobs = []
    for job_id, (_, body) in sections(top.get("jobs", ("", []))[1], 2).items():
        fields = sections(body, 4)
        needs_scalar, needs_body = fields.get("needs", ("", []))
        needs = []
        if needs_scalar.startswith("["):
            needs = [p.strip().strip("'\"") for p in needs_scalar.strip("[]").split(",") if p.strip()]
        elif needs_scalar:
            needs = [needs_scalar.strip("'\"")]
        else:
            needs = [m.group(1) for line in needs_body if (m := re.match(r"^\s+-\s+([\w-]+)\s*$", line))]
        permissions_scalar, permissions_body = fields.get("permissions", ("", []))
        permissions = mapping(permissions_body, 6)
        if permissions_scalar and not permissions:
            permissions = {"_scalar": permissions_scalar}
        job_conc_scalar, job_conc_body = fields.get("concurrency", ("", []))
        job_group = mapping(job_conc_body, 6).get("group", job_conc_scalar) or None
        jobs.append({
            "id": job_id,
            "needs": needs,
            "runs_on": fields.get("runs-on", (None, []))[0],
            "environment": fields.get("environment", (None, []))[0],
            "permissions_override": permissions or None,
            "concurrency_group": job_group,
        })
    actions = sorted(set(re.findall(r"^\s+- uses:\s*([^\s#]+)", data, re.M)))
    flags = []
    if global_permissions[0] == "unspecified" and not permission_map:
        flags.append("default_token_permissions_unverified")
    if "pull_request_target" in events:
        flags.append("privileged_pr_trigger_review")
    if cron_lines and not global_group and not any(job["concurrency_group"] for job in jobs):
        flags.append("scheduled_without_explicit_concurrency")
    if any(not re.search(r"@[a-f0-9]{40}$", action) and not action.startswith("./") for action in actions):
        flags.append("action_refs_not_sha_pinned")
    if cron_lines and re.search(r"\$\{\{\s*secrets\.", data):
        flags.append("scheduled_job_uses_secrets_review")
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "name": top.get("name", (path.stem, []))[0].strip("'\""),
        "events": events,
        "cron": cron_lines,
        "permissions": permission_map or None,
        "concurrency_group": global_group,
        "jobs": jobs,
        "action_refs": actions,
        "review_flags": flags,
    }


def inventory(root):
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        raise ValueError("missing .github/workflows directory")
    files = sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])
    if not files:
        raise ValueError("no GitHub Actions workflows found")
    entries = [read_workflow(p, root) for p in files]
    by_cron = {}
    for item in entries:
        for expression in item["cron"]:
            by_cron.setdefault(expression, []).append(item["path"])
    return {
        "schema_version": 1,
        "disclaimer": "Source inspection only; cron presence, secrets references and catalog reads are not evidence of provider inference or a running scheduler.",
        "summary": {
            "workflow_count": len(entries),
            "scheduled_workflows": sum(bool(x["cron"]) for x in entries),
            "cron_entries": sum(len(x["cron"]) for x in entries),
            "dispatchable_workflows": sum("workflow_dispatch" in x["events"] for x in entries),
            "default_permissions_unknown": sum("default_token_permissions_unverified" in x["review_flags"] for x in entries),
            "scheduled_without_concurrency": sum("scheduled_without_explicit_concurrency" in x["review_flags"] for x in entries),
            "same_cron_expressions": {k: v for k, v in sorted(by_cron.items()) if len(v) > 1},
        },
        "workflows": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Write reproducible machine-readable JSON")
    args = parser.parse_args()
    data = inventory(args.root.resolve())
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    print("Workflow audit: {workflow_count} files, {scheduled_workflows} scheduled, {cron_entries} cron entries; no live execution inferred".format(**data["summary"]), file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
