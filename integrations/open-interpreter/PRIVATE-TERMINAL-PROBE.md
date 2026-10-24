# First private Mac terminal command proof

Status: code and mocked tests only. A real Mac command has **not** been executed through this chat.

This extends the existing private GitHub-to-SQLite worker bridge with exactly one **locally authorized** diagnostic job:

```json
{"schema":1,"id":"terminal-probe-001","kind":"terminal.probe","payload":{}}
```

With explicit local authorization, it runs only the fixed macOS binary `/usr/bin/sw_vers -productVersion` in a subprocess with a fixed 8-second timeout, without a shell, external arguments, current-user directory, or environment secrets. It accepts only a sanitized dotted macOS version number. The receipt posted on the private GitHub issue contains the fixed command identifier, verified result and limited Mac version. It never posts the raw stdout, stderr, filesystem paths, GitHub credentials or command arguments.

## What is and is not enabled

- Existing scheduled LaunchAgent and private supervisor **cannot** execute terminal.probe. Their normal worker calls never supply the required local `allow_terminal_probe` flag.
- The exact private job packet must be on a distinct private TeamRovor GitHub control repository, never the public video-engine repository.
- The Mac operator must explicitly opt in to this single command. Remote-provided `shell`, `argv`, `command`, `probe` and other payload fields are rejected.
- Existing durable SQLite deduplication, STOP, and private receipt handling apply. Unsuccessful or interrupted probes become `needs_review`; no automatic repeat execution.
- No arbitrary shell, app control, file edits, AI research, paid provider access, administrator privileges or 24/7 terminal execution has been introduced.

## First one-off real Mac proof after the separate private repo is available

Read and verify the pinned PR source. In the private control repository add `control/jobs/terminal-probe-001.json` with the fixed packet above, and include its ID in the private queue only after review.

From an authenticated Mac session with a separately scoped private GitHub token available only locally, first run the read-only validation:

```sh
python3 tools/ghost_private_control.py --repo TeamRovor/rovor-mac-control --job-id terminal-probe-001 --allow-terminal-probe
```

Then, only when that exact command has been locally approved, run:

```sh
python3 tools/ghost_private_control.py --repo TeamRovor/rovor-mac-control --job-id terminal-probe-001 --receipt-issue ISSUE_NUMBER --execute --allow-terminal-probe
```

The `ISSUE_NUMBER` is the actual private receipt issue number returned by the existing bootstrap; never accept it from a remote task packet. A trusted private issue comment with `terminal_subprocess_verified=true` and sanitized `macos_version` would provide evidence of Mac command execution, but still does not establish general shell access or unattended operation.

## Deployment gates

No test in this PR opens a terminal on the user's Mac. Hosted CI mocks the process and private GitHub interactions on Python 3.9 and 3.11. Avoid directly installing this branch or replacing the existing frozen supervisor code while other workstreams are active. After a real command and receipt are verified, extend allowed terminal operations only through distinct approved, bounded capabilities with non-replay tests and STOP enforcement.
