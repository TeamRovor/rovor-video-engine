# When Amar or Evan says “work”

Use GitHub as shared project memory. Start from **latest main**, even when your code branch is older.
The goal is useful MP3-to-cartoon output now, with native Moho Ghost Employee automation long-term.
Preserve approved source art and original narration. Final previews target 1080p60 and at least 30 seconds;
technical test success is separate from Amar's visual approval.

## One-time instruction for Evan's ChatGPT

> Work on TeamRovor/rovor-video-engine. Whenever I say “work”, read the latest main WORK.md and AGENTS.md through GitHub, then follow that startup, claim, verification and handoff workflow. Use the efficiency lane unless I give another priority. Verify your actual access; do not assume you can control this computer. Continue useful non-overlapping work and publish a precise handoff before stopping.

This establishes the instruction in that conversation. A new chat needs this prompt again (or an explicit
persistent project instruction). Repository files do not automatically configure ChatGPT or wake a computer.

## 1. Read a small, fresh briefing

Read `AGENTS.md`, `coordination/tasks.json`, `coordination/work-routing.json`, and this file from the same
main revision. Check open PRs and the selected task's linked evidence. Read the relevant branch checkpoint
and scoped code only after selecting a candidate. Do not reload all history or rerun full renders every session.
`PROJECT-LOOP.md` and `REMOTE-EVAN-GITHUB.md` give deeper collaboration and access guidance.

The JSON task queue is the only ownership/dependency record. Routing JSON adds capability and lane hints;
it is not a second task queue. Missing routing means inspect and classify, never guess. Queue `done` can
mean a tested draft is complete; inspect its evidence before assuming merged, deployed, or visually approved.

## 2. Establish capabilities and choose work

Use a stable participant/session identifier; resume only an exact matching active claim. Being on Evan's
computer does not make you the owner of the existing Keona session. Do not release a blocked or stale claim.

Confirm GitHub read/write separately from hosted Actions access, local execution, original assets, visual
inspection, and native Moho runtime. Do not print credentials or full local configuration files.
GitHub-only sessions can work on repository code, reviews and documentation. Hosted Windows tests do not
prove Evan's laptop works. A blocked local setup must not consume every session or prevent independent work.

With a local checkout that contains this helper (PowerShell supports the same command):

```sh
git fetch origin
python tools/work_brief.py --ref origin/main --participant "Evan / session-name" --lane efficiency --capability github-read --capability github-write
```

Use `py -3` on Windows or `python3` on Mac if needed. Add `--capability hosted-ci` only when established;
add `local-exec`, `original-assets`, `visual-review`, or `moho-runtime` only when actually available.
The helper is read-only, uses Python's standard library, does not fetch, and does not claim or execute work.
`--json` produces a machine-readable packet. It reads queue and routing from one resolved commit.
A local working-copy brief explicitly does not establish freshness.

**GitHub connector only:** follow exactly the same rules by reading the two JSON files. Reject done,
owned/blocked, dependency-blocked and overlapping tasks, then reject tasks missing capabilities or outside
the selected lane. Prefer your own eligible active task, then ready tasks by lowest numeric priority and ID.
No eligible task means inspect current evidence and propose one bounded independent task with scope,
acceptance and capability requirements. Add it to the shared queue/routing and claim it before implementation.
Never invent a task ID from an old document or take over someone else's active task.

Evan's default lane is Windows portability, measured cache/resume efficiency, memory and reliability.
Amar's animation lane owns speech accuracy, acting, visual quality and Moho integration. These are routing
preferences, not permission to override claims. Minimize coordination overhead: one task, one useful result,
one explicit next action. Reuse existing branches, tools and reports.

## 3. Publish the claim before editing

Use the actual relevant branch and bounded file/subsystem scopes. In main `coordination/tasks.json`, set
`status: active`, `owner`, actual UTC `updated_at`, `next_update`, `next_action`, and concrete `acceptance`.
Validate with `python tools/project_loop.py check`. Connector-only sessions must have equivalent validation
run in an authorized execution environment or existing CI before implementation; do not report unrun checks.
Use the current file blob SHA for contents updates, or a non-force commit update against the expected head.
If GitHub rejects a stale write, reread and reapply only your task change. Never replace others' queue edits.
Re-read main after publishing and check for concurrent/overlapping claims. Stop overlapping work if one appears.
A branch-only claim is proposed, not shared ownership. GitHub updates are not a distributed task lock.

## 4. Implement and verify the smallest useful result

Inspect the current worktree before changing branches; preserve uncommitted work. Use an isolated branch
from the appropriate existing development branch when needed. Do not merge experimental branches merely
to obtain coordination files. With connector access, edit the relevant branch directly through supported tools.

Fix demonstrated failures first. Run focused relevant checks, reuse valid evidence for unchanged work, and
broaden tests only for a concrete risk. Measure speed/cache improvements against the same input, settings,
commit and platform; do not invent speedup figures. Never disable correctness gates to produce a green result.
If a blocker cannot be resolved with available capabilities, record it precisely and choose independent work.

## 5. Leave a handoff another chat can act on

Publish source changes and update your existing main queue entry. Include this information in its evidence,
next action and linked PR description/checkpoint (do not create another owner table):

- Task ID, owner, exact branch and commit; PR URL; whether proposed, merged, runtime-verified or visually approved.
- What changed and which files; why it helps the MP3-to-cartoon goal.
- Exact commands, platform, results, CI run links, and checks NOT run.
- Current blocker, required input/capability, next executable action and next checkpoint.
- Status: `active` to continue, `blocked` to retain a blocked claim, `done` with evidence, or `ready` with null
  owner only after an explicit release/handoff. Preserve prior work/evidence when releasing.

Refresh main before the handoff write. Never declare a PR integrated merely because it is pushed or green.
Do not claim chats, private inputs, installations or computer state synchronize through GitHub. The next
session reads the handoff and resumes from evidence instead of repeating setup or guessing what happened.
