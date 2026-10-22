# ROVOR Open Interpreter workforce pilot

This profile is for the current Codex-based Open Interpreter CLI, supporting AGENTS.md, project-level .openinterpreter/config.toml and [agents.*] subagents. It does not install software, connect a Mac, or automatically run an all-day employee.

**Newest consolidated installation sequence:** [ONE_PASS_MAC_SETUP.md](ONE_PASS_MAC_SETUP.md). Use that guide to authenticate Terminal GitHub, clone the project safely, run preflight, test Walter, and optionally add [Graphify](GRAPHIFY.md), [OmniRoute](OMNIROUTE.md), and the selected [Agent Skills](AGENT-SKILLS.md). All optional integrations require local installation/verification; GitHub files alone do not activate them.

## Efficient coding with Ponytail

The pilot includes an instruction-only, MIT-licensed [Ponytail coding skill](../../.agents/skills/ponytail/SKILL.md), with [configuration and provenance](PONYTAIL.md). It encourages reuse and small, complete, tested edits. The upstream plugin commands and hooks are **not** installed; Open Interpreter's native skill discovery must still be verified locally. This does not bypass subscription usage limits or provide AI inference credits.

## First-name-only roles

Walter — primary visible coordinator; delegate bounded tasks, review evidence, manage continuity.
Gus — GitHub, operations, shared task queue, Evan coordination.
Mike — Mac system inspection, dependencies, safe filesystem and tooling.
Jesse — Moho Pro 14, existing Evan assets, English phoneme/viseme alignment, genuine 2D animation.
Gale — Blender, bpy, procedural 3D assets, lighting, rendering.
Jane — Final Cut Pro, FCPXML, FFmpeg, pacing, audio and final exports.
Saul — marketing strategy, captions, publishing preparation; no unauthorized posting.
Hank — read-only QA, render verification, lip-sync defects and reporting.

Role identities do not imply that separate processes are continuously active.

## Isolated pilot without disturbing existing development

The repository is **private**. An authenticated Open Interpreter GitHub connector does not automatically authenticate command-line `git clone`. Terminal must have its own Git credentials. Never enter slash commands such as `/agent` at Git's username/password prompts; GitHub account passwords do not work for Git HTTPS access.

If GitHub CLI (`gh`) is installed, authenticate with the ROVOR GitHub account:

```sh
gh auth status
# If not authenticated as an account with access to TeamRovor:
gh auth login --web --git-protocol https
gh auth setup-git
```

If `gh` is missing, install GitHub CLI using the official instructions, or use GitHub Desktop's authenticated clone interface.

From any terminal directory, create a **new** isolated checkout. These conditional commands will not launch Open Interpreter when cloning fails:

```sh
mkdir -p "$HOME/Documents/Rovor"
cd "$HOME/Documents/Rovor"
git clone --depth 1 --single-branch --branch feat/open-interpreter-workforce-20261021 https://github.com/TeamRovor/rovor-video-engine.git rovor-interpreter-pilot && cd rovor-interpreter-pilot && test -f .openinterpreter/config.toml && interpreter
```

If the checkout already exists, do not clone over it. Inspect its remote, current branch, and local modifications first. Start Open Interpreter **only** from the pilot root. Trust that project only after verifying it is the intended repository. Use `/debug-config` and `/agent` to confirm the project layer and specialist roles are actually loaded.

In the current CLI, choose an available authentication method on first run. ChatGPT sign-in may avoid separate API-key billing within applicable plan limits. Alternatively use a capable local model via a supported local provider. This config intentionally contains no model, API credential or billing setting. Verify the active model and permissions with /model, /permissions and /debug-config. Use /agent to inspect available subagents.

If `interpreter --help` shows the older Python CLI's `--custom_instructions`, `--profiles` and `--auto_run` instead of Codex-style sandbox flags, this TOML file will not give it real subagents. That older version needs separate YAML or Python configuration. Never enable auto-run or unrestricted file access merely to bypass approval.

## First inspection test

Prompt Walter:

"Identify the eight roles, read AGENTS.md, WORK.md and the shared coordination instructions. Ask Gus to summarize the next safe work item. Ask Mike to verify which creative tools are genuinely installed and available on this machine. Ask Hank to report what is verified versus untested. Read only; change no files, send no emails and publish nothing."

Expect direct evidence of actual local access, not declarations that Moho, Blender, Final Cut, GitHub or social media are connected.

## Safety and collaboration

- Project config limits concurrency to two threads and defaults to on-request approval and workspace-write sandbox.
- Do not commit secrets, local personal paths, confidential media or credentials.
- Protect existing rigs, original audio, animation sources and shared branches. Follow the canonical queue and claim protocol in AGENTS.md; do not create parallel task ownership lists.
- Edits outside the authorized workspace, deleting or moving original files, access to personal communication, public posting, payments, or release require scoped approval.
- A task runner with checkpoints, crash recovery and a scheduler is required for genuine long-running unattended work; this profile is only the first step.
- Next integrations are verified Moho MCP connectivity, Blender bpy batch rendering, FCPXML exports, media QA, and approval-based publication—none is implied by this file.
