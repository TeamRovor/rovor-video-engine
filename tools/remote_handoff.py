#!/usr/bin/env python3
"""Make an offline, GitHub-hosted handoff from the canonical task queue.

This is a repository snapshot, NOT a status probe of either person's laptop.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from project_loop import suggestions, validate

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "coordination" / "tasks.json"


def clean(value):
    """Keep one line per field and prevent pipe-separated Markdown table breaks."""
    return str(value if value is not None else "—").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def make_brief(data, source="coordination/tasks.json", revision="unknown"):
    errors, warnings = validate(data)
    if errors:
        raise ValueError("Invalid shared task queue: " + "; ".join(errors))

    tasks = sorted(data["tasks"], key=lambda task: (task["priority"], task["id"]))
    lines = [
        "# ROVOR remote development handoff",
        "",
        "**Source:** `" + clean(source) + "`  ",
        "**Checked-out revision:** `" + clean(revision) + "`  ",
        "**Evidence limit:** GitHub files and CI only. This report has NO access "
        "to Evan's Windows laptop, local PATH, running ChatGPT session, installed tools, "
        "original MP3s, or Mac Moho state.",
        "",
        "## Shared queue snapshot",
        "",
        "| Priority | Task | State | Owner | Branch |",
        "| --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        lines.append("| " + " | ".join([
            clean(task["priority"]), "`" + clean(task["id"]) + "`",
            clean(task["status"]), clean(task.get("owner") or "unclaimed"),
            "`" + clean(task["branch"]) + "`",
        ]) + " |")

    lines += ["", "## Current blockers and next actions", ""]
    for task in tasks:
        if task["status"] == "done":
            continue
        lines += [
            "### " + clean(task["id"]) + " (" + clean(task["status"]) + ")",
            "",
            "**Next:** " + clean(task["next_action"]),
            "",
        ]
        if task.get("blocker"):
            lines += ["**Blocker:** " + clean(task["blocker"]), ""]
        if task.get("next_update"):
            lines += ["**Checkpoint:** " + clean(task["next_update"]), ""]

    available = suggestions(data)
    lines += ["## Available unclaimed work", ""]
    if available:
        lines += ["- `" + clean(task["id"]) + "`: " + clean(task["title"]) for task in available]
    else:
        lines.append("No unclaimed tasks meet the dependency and scope checks.")
    lines += [
        "",
        "## Connection boundary",
        "",
        "- GitHub can share committed code, PRs, task ownership, and hosted test evidence.",
        "- GitHub-hosted Windows CI is NOT evidence that Evan's laptop is configured.",
        "- ChatGPT connections, installed tools, uncommitted work, and private media do not automatically sync.",
        "- Do not duplicate work owned by another active/blocked task. Refresh main and PRs before claiming.",
        "- Original artwork, narration, and Moho source files must not be overwritten.",
        "- Technical test success is not approval of studio-quality animation.",
        "",
        "Open [REMOTE-EVAN-GITHUB.md](REMOTE-EVAN-GITHUB.md) for the remote-only operator instructions.",
        "",
    ]
    if warnings:
        lines += ["## Non-fatal coordination warnings", ""]
        lines += ["- " + clean(warning) for warning in warnings]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=TASKS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA", "unknown"))
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.source.read_text(encoding="utf-8"))
        report = make_brief(data, source=args.source.as_posix(), revision=args.revision)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        sys.stdout.write(report)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
