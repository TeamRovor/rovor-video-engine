#!/usr/bin/env python3
"""Fail-closed schedule allowlist for ROVOR GitHub Actions.

Cloudflare's existing native worker cron (wrangler.jsonc) is the provider
execution authority; these three GitHub crons are independent auxiliary jobs.
No credentials, network, dispatch, or mutation.
"""
import argparse
from pathlib import Path
import re
import sys
from workflow_inventory import inventory

# Reviewed GitHub auxiliary clocks only. A change requires code review rather
# than silently enabling another provider dispatcher on GitHub Actions.
APPROVED = {
    "hank-cloud-watchdog.yml": ["17,47 * * * *"],
    "rovor-autonomous-discovery.yml": ["17 * * * *"],
    "rovor-ai-workflow-factory.yml": ["11 */2 * * *"],
}


def validate(report):
    errors = []
    observed = {}
    for row in report["workflows"]:
        events = row["events"]
        crons = row["cron"]
        if crons or "schedule" in events:
            observed[row["file"]] = crons
        if "schedule" in events and not crons:
            errors.append(f"{row['file']}: schedule trigger without a parsed cron")
        if crons and "schedule" not in events:
            errors.append(f"{row['file']}: cron without a parsed schedule event")
    for name in sorted(set(observed) | set(APPROVED)):
        if observed.get(name) != APPROVED.get(name):
            errors.append(f"{name}: GitHub clock changed, added or removed "
                          f"(expected={APPROVED.get(name, [])}, actual={observed.get(name, [])})")
    return errors


def check_directory(root):
    report = inventory(root)
    errors = validate(report)
    # The inventory parser intentionally supports ordinary on: blocks and
    # on: [event, ...]. Do not let an unsupported inline YAML mapping hide a
    # new schedule from the allowlist.
    for path in sorted([*root.glob("*.yml"), *root.glob("*.yaml")]):
        text = path.read_text(encoding="utf-8")
        headers = 0
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            # Valid YAML permits quoted, spaced and indented trigger keys.
            # The lightweight inventory parser only understands canonical
            # top-level 'on:' syntax. Reject all alternatives rather than
            # silently missing a GitHub cron and authorizing a dispatcher.
            match = re.match(r"""^(\s*)(?P<key>on|'on'|"on")\s*:(?P<value>.*)$""", line)
            if not match:
                continue
            headers += 1
            if headers > 1:
                errors.append(f"{path.name}: duplicate on: trigger header")
                continue
            if match.group(1) or match.group("key") != "on" or not line.startswith("on:"):
                errors.append(f"{path.name}: noncanonical on: header; use top-level unquoted on:")
                continue
            value = match.group("value").strip()
            if value.startswith("{") or value == "schedule":
                errors.append(f"{path.name}: unsupported inline on: syntax")
        if not headers:
            errors.append(f"{path.name}: missing canonical on: trigger header")
    return report, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".github/workflows"))
    args = parser.parse_args(argv)
    report, errors = check_directory(args.directory)
    print(f"Audited {report['workflow_count']} workflows; "
          f"{report['schedule_count']} GitHub cron entries")
    for name in sorted(APPROVED):
        print(f"  allowed auxiliary: {name} ({', '.join(APPROVED[name])})")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
