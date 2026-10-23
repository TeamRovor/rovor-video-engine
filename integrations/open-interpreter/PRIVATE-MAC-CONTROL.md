# Private Mac control bridge: executable v1, not host deployed

**Purpose:** get from a ChatGPT-created job in a *separate private TeamRovor GitHub repository* to one safe execution on Amar's own Mac and a status receipt on a private issue. The public `rovor-video-engine` remains the shared source tree; **it is not a trusted Mac control queue**. This source adds no self-hosted GitHub Actions runner, daemon, model provider, general shell, native Final Cut/Moho/Blender edits, or social/email capabilities.

## Current implementation

`tools/ghost_private_control.py` is a **foreground, one-exact-ID adapter** over the existing `ghost_worker.py`, not another worker or scheduler. The operator passes the private repository name and job ID. The adapter uses a `ROVOR_PRIVATE_GITHUB_TOKEN` environment variable: a **fine-grained token scoped only to the new private control repository**, with Contents **read**, Issues **write**, and Metadata **read**. Do not place it in the public repo, GitHub workflow logs, local scripts, chat messages or command-line arguments. Do not reuse an unrestricted account token. The token must be available only to the authorized local process. A private repo and token are **not yet configured or verified** by this PR.

The adapter independently checks via GitHub REST that the exact repository is private and active; `TeamRovor/rovor-video-engine` and all other public repositories are refused. It reads only `control/jobs/<exact-job-id>.json` from `main`, with <=2048 bytes and exact schema:

```json
{"schema":1,"id":"mac-link-private-001","kind":"system.ping","payload":{}}
```

`system.ping` is approved. `files.inventory` accepts only `{"subpath":"."}` **and** a separate explicit `--allow-inventory` at the Mac operator, and is restricted to a new isolated local `~/Documents/Rovor/Mac-Control-Sandbox` directory. Arbitrary instructions, imports, GUIs, file deletion, other workspaces and job types are refused. The private repo must have an existing private issue for machine-readable status receipts; its number is a **local command-line argument** and cannot be changed by a remote packet.

### One approved Mac foreground operation (after private repo and scoped token exist)

Use an already trusted locally available Mac execution tool, not the public Actions runner, to run from a reviewed pinned PR checkout. The one-shot call requires only one repo/job and the private issue number:

```sh
python3 tools/ghost_private_control.py --repo TeamRovor/PRIVATE-CONTROL-REPO --job-id mac-link-private-001
# After inspecting the dry run, authorize this exact read-only job:
python3 tools/ghost_private_control.py --repo TeamRovor/PRIVATE-CONTROL-REPO --job-id mac-link-private-001 --receipt-issue 1 --execute
```

The private fine-grained token is supplied in the process environment as `ROVOR_PRIVATE_GITHUB_TOKEN`; the example never requests or prints it. Replace `PRIVATE-CONTROL-REPO` and issue number with the *actual verified private* destination. No need to reinstall Moho, Final Cut, Blender, GitHub or Open Interpreter. `--execute` is always a separate operator decision, and this v1 is not yet scheduled. 

Each job gets its own SQLite worker DB underneath `Mac-Control-State/<job-id>`, so the existing worker can only claim **that** job, not other tasks. Completed jobs never reexecute. A crashed `running` job reports `needs_review` without automatic replay. `Mac-Control-State/STOP` or the job-specific STOP blocks new dispatch; broken/symlinked state, SQLite sidecars, workspace, and receipt markers are rejected. Receipt body includes only job ID, bounded kind, status, attempts and false native/model flags. No local paths, filename inventory, token, project content or private errors are posted. A private GitHub issue POST is retried after a network error without reexecuting the job. The receipt publication can duplicate only if the network POST succeeded before the local marker was atomically created; execution itself is deduplicated.

## Acceptance and remaining gates

- Source: targeted unit tests use a fake GitHub API and real ghost worker on hosted CI; check public-repo refusal, bad packet rejection, per-job exactly-once, STOP, symlink/path containment, failed receipt POST, token non-disclosure, source read-only status, and inventory opt-in.
- No host connection or private repo is claimed. The **new private control repository and narrowly scoped credential must exist** before an actual on-Mac test. Current connected GitHub tool has no `create_repository` capability; creating the private repo requires explicit operator action outside this chat.
- On the Mac, verify an authorized local executor actually invokes the script and the private issue receives its first real receipt. Only then consider carefully scoped recurring invocation or additional tools.
- **Never restart the existing privileged `Rovor-Mac` runner in the current public repository**. GitHub security guidance: https://docs.github.com/en/actions/reference/security/secure-use . Even with a private repo, a privileged always-on runner on a personal laptop is not automatically safe; prefer the scoped polling agent and explicit user approvals.