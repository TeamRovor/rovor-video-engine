# Shared project loop

Snapshot: 2026-10-20 UTC (2026-10-19 America/Chicago).
This page coordinates work; linked PRs, commits and test results remain the evidence.
Refresh the links before choosing work. This is not a live machine monitor.

## Goal

Improve the Rovor video engine across Mac and Windows while prioritizing professional character animation.
Preserve the exact Rovor logo, approved Evan references, original narration, and existing source work.
Successful installation or rendering does not establish animation quality.

## Current work and next useful tasks

| Workstream | Existing source | Verified status at snapshot | Next useful task |
| --- | --- | --- | --- |
| Windows and render reliability | [PR #7](https://github.com/TeamRovor/rovor-video-engine/pull/7), branch `codex/windows-reliability-v3-1` | Draft describes PowerShell setup, captions, resume, cache invalidation and diagnostics. PR says static review only; laptop runtime unverified here. | Claim a bounded Windows validation task on the existing branch: tool check, original-audio render, interrupted resume, caption correction. Record OS, commit, commands, results and output settings. Fix demonstrated failures before adding unrelated features. |
| Mac Moho bridge | [Issue #6](https://github.com/TeamRovor/rovor-video-engine/issues/6) | Issue records real document info and layer reads. Disposable tutorial copy prepared; write gate remains. | Refresh issue/comments, verify exact disposable project identity, inspect actual rig and dry-run a supported pose. Do not repeat installation or test in unsaved/source documents. |
| Evan articulation and acting | [Issue #1](https://github.com/TeamRovor/rovor-video-engine/issues/1), [PR #4](https://github.com/TeamRovor/rovor-video-engine/pull/4), [PR #5](https://github.com/TeamRovor/rovor-video-engine/pull/5) | Separate draft development chain; no production art approval established. | Read latest checkpoints, then claim a specific remaining visual defect. Preserve completed rig work and show a matched before/after sample. Do not recreate the engine or approved character. |
| Cross-platform integration | PR #7 and Issue #6 | PR #7 describes portable scene metadata for a future Moho adapter; current renderer remains independent. | Compare existing scene metadata and Moho rig requirements before implementing an adapter. Agree on units, frame rate, assets, timing and capabilities through a reviewed change. Do not invent a second scene format. |

People and machine ownership are deliberately unassigned until each participant claims work.
Evan's Windows laptop is connected to GitHub according to Amar; runner status and local tool readiness have not been independently verified in this coordination pass.

## Start every work session

1. Fetch remote changes. Read `AGENTS.md`, this page from the latest shared coordination revision, and the relevant PR/issue/checkpoint. Older feature branches must consult the remote copy rather than assuming their local copy is current.
2. Check active claims below and open PRs. Select one next task with a visible acceptance result.
3. Record a claim before implementation: participant/session, task, branch, files or subsystem, timestamp with timezone, acceptance result, and next update point.
4. Push the claim and re-fetch to check for an overlapping claim. If another session owns the same files/subsystem, choose independent work or explicitly arrange a handoff first. A local unpushed claim is not shared.
5. Work on the existing relevant branch or a small branch based on it. Do not merge experimental animation branches into the Windows branch merely to synchronize progress.

Git commits alone are not an atomic task lock. Concurrent claims must be reconciled explicitly; do not assume silence or an old timestamp releases ownership.
If this coordination change is still a draft, use its branch as the shared reference. After integration, use main as the canonical reference and include coordination updates in work PRs.

## Active claims

| Participant/session | Task | Branch | Scope | Claimed at | Acceptance result | Next update |
| --- | --- | --- | --- | --- | --- | --- |
| Codex / Amar coordination session | Build shared status checker, machine preflight and handoff validation | coordination/shared-project-loop | tools/project_loop.py, tests, coordination data, coordination CI and docs | 2026-10-20T02:40:00Z | Passing regression checks; no engine changes | After implementation and checks |
| Unclaimed | Windows runtime validation | codex/windows-reliability-v3-1 | Windows setup and render checks | — | Actual machine evidence | Before implementation |

Existing PR activity does not identify who is currently running a coding session. Confirm it through a shared claim; do not silently take ownership.

## End a session or hand off

Commit and push a concise update with:

- Task and exact commit/branch.
- What changed and why it improves the engine or animation.
- Checks actually run, OS, results and evidence links; mark unrun checks explicitly.
- Remaining blocker and exact next action.
- Claim status: active, blocked, handed off or complete.

Keep private audio, credentials, machine-specific tool paths, and large caches local. Record asset identifiers/hashes and where an authorized collaborator can obtain required inputs.
Do not claim another computer has files merely because code was pushed.

## Completion gates

- Engineering: relevant checks pass on each claimed supported OS. Separate implementation, local runtime verification, and cross-platform verification.
- Animation: show continuous character acting, speech accuracy and purposeful scene action in a normal-speed review sample. Keep technical and creative verdicts separate.
- Delivery: user-facing final previews follow Amar's 1080p60 and minimum 30-second requirement. Small internal diagnostics are not a finished deliverable.
- Review: Amar's visual approval determines production animation acceptance. Preserve originals and existing release behavior.

## What is and is not synchronized

Pushed code, claims and handoff records are shared through GitHub.
Chat histories, uncommitted work, installed tools and local assets are not automatically synchronized.
This process does not create notifications, background polling, remote access, or an Actions runner.
