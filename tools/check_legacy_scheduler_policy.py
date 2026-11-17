#!/usr/bin/env python3
"""Fail-closed static checks for the retired GitHub-to-Site scheduler.

This check intentionally never reads secrets, calls providers, or invokes a job.
It is a source guard, not evidence of the production Cloudflare cron running.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / ".github/workflows/ghost-cloud-github-scheduler.yml"
REQUIRED = (
    "workflow_dispatch:",
    "confirm_legacy_site_diagnostic:",
    "github.event_name == 'workflow_dispatch'",
    "github.ref == 'refs/heads/main'",
    "inputs.confirm_legacy_site_diagnostic == true",
    "environment: rovor-hud-production",
    "cancel-in-progress: false",
)

def errors_for(text: str) -> list[str]:
    errors = []
    # YAML top-level trigger block: only inspect children of 'on:', not comments
    # or unrelated use of the word schedule in shell commands.
    match = re.search(r"(?m)^on:\s*\n((?:^[ \t]+.*\n|^\s*\n)*)", text)
    if not match:
        errors.append("missing explicit on: event block")
    else:
        event_lines = match.group(1)
        if re.search(r"(?m)^  schedule\s*:", event_lines):
            errors.append("legacy GitHub scheduler must not regain a schedule trigger")
        if re.search(r"(?m)^  (?:repository_dispatch|workflow_call)\s*:", event_lines):
            errors.append("legacy diagnostic cannot accept autonomous external triggers")
    for token in REQUIRED:
        if token not in text:
            errors.append(f"missing legacy diagnostic guard: {token}")
    return errors

def main() -> int:
    if not LEGACY.is_file():
        print(f"FAIL: missing {LEGACY}", file=sys.stderr)
        return 1
    errors = errors_for(LEGACY.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: legacy GitHub-to-Site diagnostic remains manual, main-only, guarded")
    print("NOTE: source verification does not confirm live Cloudflare cron or model inference")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
