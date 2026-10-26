# Evan / ROVOR — GitHub-only start here

**For the one-time prompt and every subsequent “work” session, start with [WORK.md](WORK.md).** Use the current queue and capability routing rather than a task name copied from an old chat.

## Two independent ROVOR improvements

[ROVOR-MP3-FIRST-ENGINE.md](ROVOR-MP3-FIRST-ENGINE.md) describes the single-MP3 goal and split responsibilities. Evan's ChatGPT should check the live `coordination/tasks.json` queue and `coordination/work-routing.json`, then claim a currently eligible efficiency task. No fixed task ID is guaranteed available. Work on measurement-driven pipeline cost, caching and reliability using hosted CI on the existing Windows branch; leave phoneme articulation and creative quality to Amar's animation-intelligence track. The speech track has added a read-only acoustic plan QA gate (`tools/speech_plan_gate.py`); it does not itself provide a finished video. GitHub access alone cannot run or install tools on Evan's laptop.

**Use this even if nobody can visit Evan's laptop.** The only connection we can currently rely on is the existing GitHub access from Evan's ChatGPT. That access shares repository contents, not his Windows desktop, terminal, installed programs, MP3 library, or ChatGPT conversation.

## Start a fresh Evan ChatGPT conversation

Ask the connected ChatGPT to do the following, using its GitHub connector only:

> Continue the existing ROVOR video engine at `TeamRovor/rovor-video-engine`. Read the **latest main** versions of `AGENTS.md`, `PROJECT-LOOP.md`, `coordination/tasks.json`, and `REMOTE-EVAN-GITHUB.md`; check current open PRs, including [Windows PR #7](https://github.com/TeamRovor/rovor-video-engine/pull/7). First state what the GitHub connection can actually read/write and what local laptop operations it **cannot** verify. Do not start a second renderer, repeat completed tasks, overwrite source art, or assume you can run commands on this Windows laptop. Choose a *free, non-overlapping* task, claim it in the shared main queue before editing, implement in the existing appropriate branch, and publish test evidence and a handoff. If only GitHub access is available, work on code, CI and documentation on GitHub. Never represent GitHub-hosted Windows test results as proof this laptop is configured. The final animation target is 1080p60, at least 30 seconds, and requires Amar's visual approval.

A ChatGPT session that can only read GitHub can still explain the next useful tasks. It must not claim it has pushed a change, installed anything, or synced its conversation until that action is actually verified.

## One shared operating loop

1. **Read fresh main:** [Task queue](coordination/tasks.json), [instructions](AGENTS.md), [priorities](PROJECT-LOOP.md), and the [GitHub-only handoff Actions run](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/remote-handoff.yml). Check open PRs and linked issue evidence too.
2. **Do not duplicate owners:** `active` and `blocked` tasks reserve their scopes. The audio import is a separate ongoing task; don't start another MP3 import or promise the files exist until confirmed in the repository.
3. **Claim before work:** Record the task, owner, real timestamp, branch, non-overlapping scope, acceptance check and next checkpoint in **main** `coordination/tasks.json`. Re-read main after pushing to spot concurrent claims. Do not pretend the queue is an atomic lock.
4. **Use existing branches:** [PR #7](https://github.com/TeamRovor/rovor-video-engine/pull/7) is Windows and render reliability. [Issue #6](https://github.com/TeamRovor/rovor-video-engine/issues/6) is Mac Moho bridge. [PR #5](https://github.com/TeamRovor/rovor-video-engine/pull/5) is Evan acting. Keep experimental assets separate; preserve originals.
5. **Report truthfully:** Push source changes, identify exact branch and commit, record GitHub Actions run URLs and any failing checks, then hand off or close your task. Uncommitted local files, tools and chats are **not** synchronized by GitHub.

## What can happen from GitHub alone?

| Activity | Without laptop access |
| --- | --- |
| Read and modify repository code (if connector has write permission) | Yes |
| File an issue or update a shared task claim | Yes, with GitHub write permission |
| Review Windows development PR #7 | Yes |
| Run GitHub Actions on hosted Windows/macOS/Linux machines | Only if workflow access and permissions permit; results describe hosted runners |
| Repair code based on CI failures | Yes, via GitHub edits and another run |
| Install FFmpeg, Node, Rhubarb or Whisper on Evan's computer | **No** |
| Check `local_tools.json`, PATH, original MP3 or running render on his laptop | **No** |
| Automatically copy an MP3 or Mac Moho source file across machines | **No** |
| Transfer the two ChatGPT conversations or control Evan's screen | **No** |

## The known Windows setup blocker

The shared task `windows-runtime` records missing `evan-engine/local_tools.json`, unavailable local narration, and FFmpeg / FFprobe / Rhubarb / npm not detected on the actual Windows runtime. That evidence is separate from **passing GitHub-hosted Windows regressions**. Do not repeatedly ask Amar to visit the laptop.

The latest Windows branch has `install-on-windows.ps1`, launcher `--check`, `workspace_status.py --fetch`, and `evan_workspace_status`. If Evan's ChatGPT truly has permission to execute commands on his machine, it may offer to run these **read-only** diagnostics after checking his current worktree. Otherwise use repository code and hosted CI, and document the missing local execution capability.

## Remote status report — GitHub-hosted only

Open [GitHub-only remote handoff workflow](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/remote-handoff.yml). Its latest successful run includes an easy-to-read **Job summary** describing the current task queue, owners, next actions, and blockers, plus a downloadable `remote-handoff-brief` artifact. You can also manually dispatch the workflow if you have GitHub permissions. It reads the repository, not Evan's laptop.

The source for that report is `tools/remote_handoff.py`; run locally on any checkout using:

```sh
python tools/remote_handoff.py --output handoff-brief.md
```

**Keep moving remotely:** Prioritize unclaimed work such as verifying animation defects from existing samples and safe Moho sandbox investigations where actual access is established. Windows code and CI can continue independently, but any claim of an end-to-end render on Evan's laptop must be backed by a run on that laptop.
