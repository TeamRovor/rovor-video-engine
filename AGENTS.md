# Windows branch session entrypoint

This branch is the existing Windows/reliability work for PR #7. Continue that work; do not recreate the engine.

The shared coordination system is now on main (merged PR #8). Before choosing a task, fetch remote state and read the canonical instructions, priorities and task claims:

```sh
git fetch origin
git show origin/main:AGENTS.md
git show origin/main:PROJECT-LOOP.md
git show origin/main:coordination/tasks.json
git show origin/main:coordination/README.md
```

These Git commands work in PowerShell and macOS terminals. If fetching fails, report that the shared state may be stale; do not assume an old local task queue is current.

Follow those instructions before implementation and at handoff. A claim must be recorded in the shared main queue and rechecked for overlap before starting. Update that queue through a separate coordination change; do not merge this unfinished renderer branch into main to publish a claim. Preserve other sessions' work and local changes.

If tools/project_loop.py is available in this checkout, use its status/check commands as described in the shared README. If it is absent, read the fetched shared queue with git show above; do not install or recreate a second coordination helper.

Keep Windows implementation separate from machine validation. Tool detection or static review does not prove a successful render on Evan's laptop. Record the exact commit, platform, commands, results and evidence. Respect existing character/source preservation and Moho disposable-project gates.

Pushed code and task records are shared; chat histories and uncommitted work are not. Do not claim the other laptop or AI session has received this update until it has fetched/pulled and read it.
