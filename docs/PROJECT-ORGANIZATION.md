# ROVOR repository map

This is a navigation guide, not a second roadmap or task tracker. Refresh the linked files on `main` before acting; the shared queue and current PRs can change.

## Start here

1. [`AGENTS.md`](../AGENTS.md) — safety boundaries, collaboration rules and required project references.
2. [`WORK.md`](../WORK.md) — what to do when a session is told to work; capability checks, task selection, claiming and handoff.
3. [`ROVOR-AI-PLAN.md`](../ROVOR-AI-PLAN.md) — canonical product direction and staged roadmap.
4. [`coordination/tasks.json`](../coordination/tasks.json) — **single source of truth** for task status, ownership, dependencies, scope and next action.
5. [`coordination/work-routing.json`](../coordination/work-routing.json) — capability/lane hints and requirements; it does not assign ownership.
6. [`architecture/CHATGPT-WORKFLOWS.md`](../architecture/CHATGPT-WORKFLOWS.md) — match available tools to the deliverable and define evidence.

## Where to look by kind of work

| Need | Start with | Keep in mind |
| --- | --- | --- |
| Current work, owners, blockers | [Task queue](../coordination/tasks.json), then [open pull requests](https://github.com/TeamRovor/rovor-video-engine/pulls) and linked issues | Queue data is not proof of current runtime; refresh external evidence and check for concurrent work. |
| Session coordination and validation | [`coordination/README.md`](../coordination/README.md), [`PROJECT-LOOP.md`](../PROJECT-LOOP.md), [`tools/project_loop.py`](../tools/project_loop.py) | Validate queue edits with `python tools/project_loop.py check` in a checkout containing the tool. |
| GitHub-only Evan handoff | [`REMOTE-EVAN-GITHUB.md`](../REMOTE-EVAN-GITHUB.md) | Repository access is not laptop, installed-software, source-media or native-app access. |
| Animation and original narration | [`ROVOR-MP3-FIRST-ENGINE.md`](../ROVOR-MP3-FIRST-ENGINE.md), [Issue #1](https://github.com/TeamRovor/rovor-video-engine/issues/1), relevant animation PRs | Preserve approved artwork and source audio. Automated tests do not equal artistic approval. |
| Windows engine setup and rendering | [PR #7](https://github.com/TeamRovor/rovor-video-engine/pull/7), [`evan-engine/`](../evan-engine/) | Hosted CI does not verify Evan's actual Windows laptop or local toolchain. |
| Moho bridge and native pose evidence | [Issue #6](https://github.com/TeamRovor/rovor-video-engine/issues/6), relevant `tools/moho_*` files | Do not repeat setup or write to original projects; follow disposable-project identity and dry-run gates. |
| Shared render/job infrastructure | [`tools/`](../tools/), [`tests/`](../tests/), [`.github/workflows/`](../.github/workflows/) | Reuse the existing pipeline and tests; don't introduce a parallel renderer or queue without an explicit need. |
| Rovor brand, business knowledge and delivery | [`business/knowledge/README.md`](../business/knowledge/README.md), [proof catalog](../business/proof-catalog.md), [playbooks](../business/playbooks/) | Distinguish verified evidence, concepts, unfinished demos and approved claims. |
| Architecture and reusable workflow quality | [`architecture/`](../architecture/), especially [evaluations](../architecture/evaluations/) | Capability maps and evaluation examples support decisions; neither replaces the task queue. |

## Safe contribution loop

1. Read the current queue, routing and relevant open PR/issue; confirm the task is eligible and no scope overlaps.
2. Use a bounded existing task and branch where possible. Record a claim in the canonical queue before implementation, following `coordination/README.md`; do not edit `main` directly for implementation.
3. Change the smallest relevant set of files. Keep source media, credentials and machine-specific configuration out of public commits.
4. Run the checks available in the current environment. Record exact commands, revision and results; clearly mark checks that need a real Mac/Windows host or human visual review.
5. Publish a reviewable PR and update the task's next action/evidence only when the change and checks are real.

## Fast coordination health check

From a fresh checkout, run:

```sh
git fetch origin
python tools/project_loop.py status --ref origin/main
python tools/project_loop.py doctor
```

- `status` validates the canonical queue, prints warnings/errors, shows next actions and lists tasks whose dependencies and scopes currently permit a claim. It does not claim work or inspect unpushed changes in other sessions.
- `doctor` reports local environment/working-tree facts only. A tool found on PATH is not proof that the production workflow works.
- Treat an old-claim warning as a prompt to confirm ownership, not permission to take over. A blocked task keeps its owner; resolve the blocker or coordinate a handoff.
- If no task is eligible, do not bypass dependencies or create a second queue. Refresh open PRs/issues and routing, then select a genuinely independent existing task or document the concrete blocker.

## Status vocabulary

- **Implemented:** a code or document change exists.
- **Tested:** the named check ran and its result is recorded.
- **Host-verified:** the required native machine/application actually ran the workflow.
- **Visually approved:** the intended reviewer inspected the actual output at normal speed/resolution.
- **Merged/deployed:** the corresponding GitHub or deployment state confirms it.

Do not treat these states as interchangeable. This guide is only an index; detailed requirements and live state remain in the linked source files.
