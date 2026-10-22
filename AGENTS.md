# “Work” session entrypoint

When the user says **work**, read [ROVOR-AI-PLAN.md](ROVOR-AI-PLAN.md) and follow [WORK.md](WORK.md) from latest main. **ChatGPT-first is the current strategy; local-PC execution is a later phase.** Video is one capability of the broader Rovor Digital AI. Use `architecture/CHATGPT-WORKFLOWS.md` for present tool selection; do not restart the project as a video-only engine or prematurely build a replacement local assistant. It defines capability-aware selection, shared claims, efficient execution and evidence-based handoffs. Read `coordination/work-routing.json` alongside the canonical task queue; the routing file does not assign ownership.

# Repository collaboration instructions

**Parallel development boundary:** Read [ROVOR-MP3-FIRST-ENGINE.md](ROVOR-MP3-FIRST-ENGINE.md). Evan's GitHub-connected session should use the efficiency lane in WORK.md and select a currently eligible task from the live queue; never assume an old task suggestion is still available; do not assume he has actually claimed it or that his laptop is remotely controllable. Amar's animation-intelligence track owns phoneme/viseme accuracy and acting QA through the existing art workstreams and `tools/speech_plan_gate.py`; do not duplicate its files. A green QA report remains **not** a finished/approved MP3-to-cartoon film.

**GitHub-only Evan/Windows handoff:** When the only confirmed access is Evan's ChatGPT GitHub connector, read [REMOTE-EVAN-GITHUB.md](REMOTE-EVAN-GITHUB.md) before choosing work. The [remote handoff workflow](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/remote-handoff.yml) publishes a read-only task/owner/blocker summary from the shared queue. It does not access Evan's laptop. Never assume terminal, installer, narration, or runtime access merely because the GitHub connector works.

Read PROJECT-LOOP.md and coordination/tasks.json before selecting work. Use coordination/README.md for the session commands. The JSON task queue is the single ownership/dependency record; do not create a parallel claim table. Run `python tools/project_loop.py check` before pushing queue changes. Fetch and consult the latest shared coordination revision, current PRs/issues and relevant branch checkpoint. On older branches, read the remote coordination copy; do not assume a missing local file means there is no shared plan.

Before implementation, record and push a bounded task claim with participant/session, branch, scope, timestamp, acceptance result and next update point. Re-fetch and resolve overlapping claims. Never overwrite another session's work or infer a task is abandoned from silence. Use independent files/tasks while an overlapping owner remains active.

Continue existing work. Windows setup and render reliability currently belong to PR #7; Moho bridge evidence is in Issue #6; character quality requirements are in Issue #1 and draft PRs #4/#5. Refresh those sources because their status can change. Do not restart completed setup, invent a replacement renderer, or combine divergent experimental branches solely to keep machines synchronized.

Keep changes focused and reversible. Preserve original artwork, narration and native project files. Follow the existing disposable-project identity and dry-run gates for Moho edits. A GitHub connection does not prove runner availability or local tool readiness.

Record exact commands/checks, OS, commit and evidence. Distinguish implemented, runtime-verified, and visually approved. Never call tool registration a live Moho connection or tests/render success studio-quality animation.

At handoff, push changes and update the shared record with completed work, checks actually run, blockers, exact next action and claim status. Keep machine-specific executable paths, private recordings, secrets and caches out of commits. Do not claim chat histories or local files synchronize automatically.

User-facing final previews target 1080p60 and at least 30 seconds. Internal diagnostic samples may be shorter but must be labeled as diagnostics. Amar's visual review determines production animation acceptance.

**Business efficiency:** For business operations, sales or delivery work, follow `business/OPERATING-SYSTEM.md`.
Use the same task queue and capability router. Tie new work to a measurable business outcome; distinguish
proposed measures from actual results. The operations reporter only prepares read-only work packets; it
has no authority to claim tasks, send messages, publish, spend, or operate a personal computer.

## Open Interpreter pilot (opt-in)

When this repository is opened with a compatible Open Interpreter CLI, the primary conversational coordinator is **Walter**. The optional specialist agents are **Gus** (operations), **Mike** (Mac systems), **Jesse** (Moho/2D), **Gale** (Blender/3D), **Jane** (video editing), **Saul** (marketing), and **Hank** (QA). Refer to these roles by first names only. Consult [the Open Interpreter pilot guide](integrations/open-interpreter/SETUP.md) and its [scoped subagent configuration](.openinterpreter/config.toml). These are supplemental to—not replacements for—the established WORK.md, task queue, source preservation, ownership and quality requirements above. Do not claim a local Mac or remote collaborator is connected until verified.

## Ponytail coding-efficiency policy (pilot)

For code-writing, bug-fixing, refactoring and technical review, use the local [Ponytail skill](.agents/skills/ponytail/SKILL.md) as optional implementation guidance: examine callers and existing helpers first, make the smallest *complete* change, reuse dependencies, and leave a focused test for nontrivial logic. Preserve ROVOR's existing task claims, asset protections, tests, QA and explicit user requirements; efficiency never excuses unfinished work. Walter should handle small tasks directly rather than spawning several personas solely to restate the same context. Ponytail is a coding skill, **not** a local model or a substitute for inference credits. Installation and provenance: [PONYTAIL.md](integrations/open-interpreter/PONYTAIL.md).

## Optional research, routing and context tools (Mac pilot only)

- [Graphify](integrations/open-interpreter/GRAPHIFY.md): prefer a narrow query of an **existing, current, locally generated** code graph over repeatedly reading the full codebase. Indexing is opt-in and **code-only with GRAPHIFY_BACKEND=none** unless user explicitly authorizes other processing. A generated graph is not the source of truth or shared team memory.
- [OmniRoute](integrations/open-interpreter/OMNIROUTE.md): optional third-party AI gateway. Never switch model/provider, spend money, distribute files to external services or assume an available free tier without verified configuration and authorization. Keep the existing Open Interpreter provider until tested.
- [Context Engineering](.agents/skills/context-engineering/SKILL.md) and [Debugging and Error Recovery](.agents/skills/debugging-and-error-recovery/SKILL.md): consult **on demand**, not on every request. Do not load all third-party skills or spawn agents indiscriminately. [Integration details](integrations/open-interpreter/AGENT-SKILLS.md).
- For Mac setup, read [the consolidated one-pass guide](integrations/open-interpreter/ONE_PASS_MAC_SETUP.md) and run its read-only preflight before claiming integrations are active.


## Research-first software specialists

When Jane is assigned Final Cut Pro work, read [her Final Cut research and MCP pilot guide](integrations/final-cut-pro/README.md), [specific study missions](integrations/final-cut-pro/RESEARCH-PACKET.md), and the reusable [software integration research skill](.agents/skills/software-integration-research/SKILL.md). Jesse/Gale and future software specialists may reuse the skill for Moho/Blender/other programs. Primary-source research, configuration, actual local tool handshake, reversible native edit, production-quality result and unattended ghost worker are distinct milestones; never conflate them. The project fcpxml MCP entry is disabled by default with invalid sandbox placeholders; nobody should enable/install a third-party application adapter without Mac-owner approval and actual scoped path verification. Existing Blender MCP and prior Open Interpreter Mac error remain independent. All specialists use WORK.md and the existing canonical task queue; no separate ghost-employee ownership lists.
