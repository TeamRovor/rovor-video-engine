# Shared session check

The task queue in `coordination/tasks.json` is the ownership/dependency record.
`PROJECT-LOOP.md` explains priorities and links to detailed evidence. Do not maintain a second ownership table there.
This tool uses only Python's standard library. It does not fetch, push, claim tasks or operate Moho.

## Start in a checkout containing this change

Fetch remote state first, then run:

```sh
git fetch origin
python tools/project_loop.py status
python tools/project_loop.py doctor
```

Use `python3` on a Mac where `python` is unavailable. On Windows use `py -3` if needed.
These commands work in a normal terminal or PowerShell. No installer or new paid service is needed.

Before this change is merged, the shared source is `origin/coordination/shared-project-loop`:

```sh
python tools/project_loop.py status --ref origin/coordination/shared-project-loop
```

After integration, use `--ref origin/main`. A feature branch may contain older task data; the ref option reads the fetched shared record without switching branches or touching local work.
The helper itself must exist in your checkout. Older checkouts can read the shared files with `git show origin/coordination/shared-project-loop:coordination/tasks.json` until the coordination files are integrated. Never merge experimental render code just to obtain these files.

The tool prints available tasks after excluding unfinished dependencies and overlapping active/blocked scopes.
It does not select a task for you. Refresh linked PRs/issues because the queue cannot see other people's unpushed work.

## Claim, work, hand off

Edit the existing task, rather than adding a duplicate:

- Set `status` to `active`, `owner` to a participant/session identifier, `updated_at` to the actual ISO timestamp with timezone, and `next_update` to a concrete checkpoint.
- Set `scopes` to the actual files/directories you will edit or a shared `subsystem:name` for a machine/resource. Use forward slashes with no trailing slash. Different names for the same resource will not be recognized as overlapping; agree on names first.
- Validate, commit and push the claim to the current shared coordination branch. If using a PR for a claim, it is proposed until integrated into the shared record. Re-fetch and inspect for conflicting claims before implementation. Git pushes/PRs are not a distributed lock.
- Work on the existing feature branch; keep machine-specific paths and inputs local.
- At each handoff update `next_action`, `updated_at`, `next_update` and blocker as applicable. `blocked` retains ownership; an old claim only generates a warning.

```sh
python tools/project_loop.py check
```

To finish, set `status` to `done` and add evidence objects with `commit`, `platform`, `check`, `result`, and `reference` fields. A reference can be a workflow URL or committed report path. Keep enough context to reproduce the result. Explicitly record unrun checks; do not convert a failure into a completion claim.

The checker validates structure and ownership conflicts. It cannot verify that evidence is truthful, evaluate animation quality, prevent bypassing checks, or guarantee every participant follows the protocol. Do not treat the green coordination check as Windows runtime, Moho, or art approval.

## Automated verification

The workflow runs coordination validation and regression checks on GitHub-hosted Linux, Windows and macOS for relevant pull requests and pushes to main. It has read-only repository permissions and never runs on either person's laptop. It does not post messages or require a personal access token.

The workflow cancels outdated runs for the same pull request. It only runs when coordination data/tooling changes, avoiding full video renders for handoff edits. The initial Windows engine task remains unverified until evidence comes from Evan's actual setup.
