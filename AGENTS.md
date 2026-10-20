# Repository collaboration instructions

**Parallel development boundary:** Read [ROVOR-MP3-FIRST-ENGINE.md](ROVOR-MP3-FIRST-ENGINE.md). Evan's GitHub-connected session may claim the *currently unclaimed* `engine-efficiency-benchmarks` task for hosted cross-platform profiling and cache/restart efficiency; do not assume he has actually claimed it or that his laptop is remotely controllable. Amar's animation-intelligence track owns phoneme/viseme accuracy and acting QA through the existing art workstreams and `tools/speech_plan_gate.py`; do not duplicate its files. A green QA report remains **not** a finished/approved MP3-to-cartoon film.

**GitHub-only Evan/Windows handoff:** When the only confirmed access is Evan's ChatGPT GitHub connector, read [REMOTE-EVAN-GITHUB.md](REMOTE-EVAN-GITHUB.md) before choosing work. The [remote handoff workflow](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/remote-handoff.yml) publishes a read-only task/owner/blocker summary from the shared queue. It does not access Evan's laptop. Never assume terminal, installer, narration, or runtime access merely because the GitHub connector works.

Read PROJECT-LOOP.md and coordination/tasks.json before selecting work. Use coordination/README.md for the session commands. The JSON task queue is the single ownership/dependency record; do not create a parallel claim table. Run `python tools/project_loop.py check` before pushing queue changes. Fetch and consult the latest shared coordination revision, current PRs/issues and relevant branch checkpoint. On older branches, read the remote coordination copy; do not assume a missing local file means there is no shared plan.

Before implementation, record and push a bounded task claim with participant/session, branch, scope, timestamp, acceptance result and next update point. Re-fetch and resolve overlapping claims. Never overwrite another session's work or infer a task is abandoned from silence. Use independent files/tasks while an overlapping owner remains active.

Continue existing work. Windows setup and render reliability currently belong to PR #7; Moho bridge evidence is in Issue #6; character quality requirements are in Issue #1 and draft PRs #4/#5. Refresh those sources because their status can change. Do not restart completed setup, invent a replacement renderer, or combine divergent experimental branches solely to keep machines synchronized.

Keep changes focused and reversible. Preserve original artwork, narration and native project files. Follow the existing disposable-project identity and dry-run gates for Moho edits. A GitHub connection does not prove runner availability or local tool readiness.

Record exact commands/checks, OS, commit and evidence. Distinguish implemented, runtime-verified, and visually approved. Never call tool registration a live Moho connection or tests/render success studio-quality animation.

At handoff, push changes and update the shared record with completed work, checks actually run, blockers, exact next action and claim status. Keep machine-specific executable paths, private recordings, secrets and caches out of commits. Do not claim chat histories or local files synchronize automatically.

User-facing final previews target 1080p60 and at least 30 seconds. Internal diagnostic samples may be shorter but must be labeled as diagnostics. Amar's visual review determines production animation acceptance.
