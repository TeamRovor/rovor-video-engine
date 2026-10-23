# ROVOR session routing: one queue, one capability check

**Scope:** This is a workflow improvement, not a second queue, an AI persona registry, a Mac remote executor, or a background scheduler.

## Why this exists

Earlier the shared `coordination/tasks.json` contained 74 tasks but only 18 had explicit classifications in `coordination/work-routing.json`. This branch classifies all 75 tasks present at the time of the audit. The two files remain separate for a reason:

- `coordination/tasks.json` is the **only owner, priority, dependency, evidence and status record**.
- `coordination/work-routing.json` maps task IDs to a **lane and required confirmed capabilities**, nothing more.
- `tools/work_brief.py` reads both from the same exact Git commit. It **never** changes either file, assigns owners, calls models, starts a computer, or performs jobs.

New tasks **must** get an explicit routing entry before an assistant claims them. Unclassified tasks fail closed, and the coverage count exposes the omission. Do not guess from the task name, owner name or app icon.

## Select eligible work without hijacking another session

1. Fetch *latest main*. In a local checkout: `git fetch origin`.
2. Identify this exact active session and only the capabilities it can actually use. GitHub connection does **not** imply Mac/Windows execution.
3. Read the brief against that fetched commit, not locally modified files:
   ```sh
   python3 tools/work_brief.py --ref origin/main --participant "Evan / Windows research chat" --lane efficiency --capability github-read --capability github-write --capability hosted-ci --fallback-any-lane --json
   ```
4. Only if the selected task is **ready** and nonconflicting: claim it in the canonical queue with owner, scoped paths, timestamps and acceptance. Re-read main after the claim to detect a concurrent claim.
5. Only an exact matching owner may resume an **active** task. **Blocked** tasks never resume automatically, even for the original owner. **Done** is source-task completion, not production approval.
6. Execute only within the abilities actually verified for this session; publish evidence (specific tests, video/art review, branch SHA, failures), and update the existing queue entry.

`--fallback-any-lane` is **opt-in**: when the requested lane has no eligible job, the brief may suggest a different lane, *but* still checks scope, task status, dependency completion and every declared capability. When there is an eligible requested-lane task, it is always preferred even if a higher-priority task exists in another lane. Without the flag, lane selection remains strict.

## Practical job lanes

| Lane | Typical work | Abilities that must be verified when required |
|---|---|---|
| efficiency | Windows portability, render caching and measured reliability | hosted-ci; sometimes local-exec and original-assets |
| animation | Original character art, narration timing, physics and artistic quality | original-assets, visual-review, hosted-ci |
| integration | Moho, Blender, Final Cut, safe cross-app interfaces | hosted-ci, local-exec and app runtime only when actually needed |
| operations | Bounded local workers, business operations and recoverability | hosted-ci; local-exec only for on-device acceptance |
| coordination | Queue, routing, handoff hygiene | GitHub read/write, hosted CI if running tests |
| sales/delivery | Sourced offers, requirements and deliverables | Do not invent proof or send/publish without authority |

`blender-runtime` and `final-cut-runtime` must **never** be inferred from a GitHub repository, a plugin install, or a saved config; only a witnessed usable app session supports declaring them. Similarly, a GitHub-hosted test does not prove a laptop is online.

## When no task is eligible

A truly idle session should **not** invent a completion claim, take over a stale owner, or restart blocked Mac setup. Use the brief's `routing_coverage`, `excluded` reasons, and existing open PRs to identify one independent, narrowly scoped improvement that can be tested with available capabilities; claim it before changing anything. If a dependency can only be satisfied on a missing host, record that exact blocker and choose useful unrelated work.

If `routing_coverage.unclassified_unfinished` contains IDs, classify those **before** selecting them; do not run an unnamed fallback. The CI route test detects missing mappings.

## Test commands (offline, no laptop runtime)

```sh
python3 tools/project_loop.py check
python3 -m unittest discover -s tests -p 'test_work_brief.py' -v
```

The GitHub Actions `work-brief-routing-check.yml` runs those checks on Python 3.9 and 3.11 without a self-hosted runner. Passing confirms only the router and queue structure, **not** actual Open Interpreter, Final Cut, Blender, Mac/Windows local work, external model calls, or ghost employees running unattended.
