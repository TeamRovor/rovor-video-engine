#!/usr/bin/env python3
"""Read-only PR path-collision advisory. Not a merge-conflict verdict.

The GitHub engineering lane can review overlap before producing duplicate work.
Only exact paths on the same base branch are compared; stacked PRs are excluded.
"""
import json
import os
import sys
from urllib.request import Request, urlopen


def overlapping_prs(current, others):
    paths = set(current.get("files") or [])
    if not paths:
        return []
    matches = []
    for pr in others:
        if pr.get("number") == current.get("number") or pr.get("base") != current.get("base"):
            continue
        if not isinstance(pr.get("files"), list):
            continue
        common = sorted(paths.intersection(pr["files"]))
        if common:
            matches.append({"number": pr["number"], "paths": common})
    return sorted(matches, key=lambda row: row["number"])


def github_json(path, token):
    request = Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "rovor-pr-overlap-audit",
        },
    )
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def files_for(repo, number, token):
    paths = []
    complete = True
    for page in range(1, 4):
        rows = github_json(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}", token)
        if not isinstance(rows, list):
            raise ValueError("Unexpected PR file response")
        for row in rows:
            if (not isinstance(row, dict) or
                    not isinstance(row.get("filename"), str) or
                    not row["filename"]):
                # Invalid GitHub data must not make a partial audit look complete.
                raise ValueError("Unexpected PR file entry")
            paths.append(row["filename"])
        if len(rows) < 100:
            break
        if page == 3:
            complete = False
    return paths, complete


def escape_warning(value):
    return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not token or not event_path or len(repo.split("/")) != 2:
        print("Skipping PR overlap audit: no Actions PR context.")
        return 0
    with open(event_path, encoding="utf-8") as stream:
        event = json.load(stream)
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        print("Skipping PR overlap audit: not a PR event.")
        return 0
    current = {"number": pr["number"], "base": pr["base"]["ref"]}
    current["files"], current_complete = files_for(repo, current["number"], token)
    opened = github_json(
        f"/repos/{repo}/pulls?state=open&sort=updated&direction=desc&per_page=100", token
    )
    if not isinstance(opened, list):
        raise ValueError("Unexpected open PR response")
    same_base = [
        p for p in opened
        if p["number"] != current["number"] and p["base"]["ref"] == current["base"]
    ]
    # Bound REST calls on busy repositories; never claim an exhaustive audit.
    candidates = same_base[:25]
    peers = []
    complete = current_complete and len(opened) < 100 and len(same_base) <= 25
    for peer in candidates:
        filenames, all_files = files_for(repo, peer["number"], token)
        complete = complete and all_files
        peers.append({"number": peer["number"], "base": current["base"], "files": filenames})
    collisions = overlapping_prs(current, peers)
    print(f"PR #{current['number']}: {len(peers)} same-base PRs inspected; "
          f"{len(collisions)} overlapping change sets; "
          f"{'complete within API bounds' if complete else 'PARTIAL AUDIT'}")
    for overlap in collisions:
        shown = ", ".join(overlap["paths"][:8])
        extra = len(overlap["paths"]) - 8
        if extra > 0:
            shown += f" (+{extra} more)"
        message = f"PR #{overlap['number']} also edits {shown}; reconcile ownership before merge."
        print("::warning title=Overlapping PR files::" + escape_warning(message))
    if not complete:
        print("::warning title=Partial PR overlap audit::"
              "Review all open PRs manually; API or candidate cap prevents full coverage.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        # This check is advisory. Transport failure must not turn a passing
        # offline safety test into a misleading PR conflict conclusion.
        print("::warning title=PR overlap check unavailable::"
              + escape_warning(type(exc).__name__)
              + "; no merge-safety conclusion was reached.")
        sys.exit(0)
