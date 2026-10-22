# ROVOR read-only Mac LaunchAgent — opt-in prototype

**Status:** configuration generator only; not installed or running on Amar's Mac. This stacked change depends on [draft PR #32](https://github.com/TeamRovor/rovor-video-engine/pull/32) (SQLite job worker) and [draft PR #33](https://github.com/TeamRovor/rovor-video-engine/pull/33) (foreground loop). It does not enable Blender, Moho Pro, Final Cut Pro, email, publishing, AI reasoning, screen control, destructive file operations, login/password access or wake-from-sleep.

`tools/ghost_launchd.py` generates a macOS *user* LaunchAgent plist in your selected private state directory. It **never** executes `launchctl`, installs the plist, runs the worker, creates credentials or configures login autostart. Only an operator who explicitly copies and bootstraps it activates scheduling.

## Safety / bounds

- Fixed label: `com.rovor.ghost-worker.readonly`; fixed adapter allowlist remains `system.ping` and `files.inventory` from `tools/ghost_worker.py`.
- Default `StartInterval=600` seconds (10 minutes), `RunAtLoad=true`, `KeepAlive=false`; max 25 jobs, max 120 seconds, idle polling 2 seconds per launch. Accepted intervals 300–3600 seconds, max 1–100 jobs, and max 10–240 seconds with at least 60 seconds below interval.
- Arguments are a structured launchd array: no `/bin/sh`, interpolated commands or credentials. Logs remain in a private local state directory, not GitHub.
- Requires a private state folder (`chmod 700`), a separate non-nested authorized workspace, an existing worker and loop, and a real absolute Python executable. Rejects symlink folders/worker scripts and differing existing plists. Repeated identical generation is safe.
- STOP marker from the existing loop stops work between jobs but **does not unload the LaunchAgent**; `launchctl bootout` disables scheduled launching. Existing jobs and receipts persist in local SQLite.

## First verify in a disposable folder on the actual Mac

From your *local checkout of the stacked branch* `feature/rovor-ghost-launchd-v1` (Python 3.11+):

```sh
mkdir -p "$HOME/rovor-worker-smoke"
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" init
python3 -m unittest discover -s tests -p 'test_ghost*.py' -v
python3 tools/ghost_launchd.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke"
plutil -lint "$HOME/.rovor-worker-smoke-state/com.rovor.ghost-worker.readonly.plist"
```

This generates a plist **only**. Confirm the printed `installed: false` and `started: false`, review paths and inspect with `plutil -p`. Do not point the early prototype at all of your home folder, real downloads, client files, credentials, or original Evan project assets. The example assumes `python3` resolves to Python 3.11+; if it does not, choose an installed 3.11+ executable and call it explicitly.

## Optional operator-only activation, after successful smoke tests

No command below is run by the generator or by this GitHub PR. **Only do this if you want to opt in** to read-only scheduled operations on that Mac user session:

```sh
mkdir -p "$HOME/Library/LaunchAgents"
# Check that the destination does not exist before copying; do not overwrite other agents.
test ! -e "$HOME/Library/LaunchAgents/com.rovor.ghost-worker.readonly.plist" || { echo 'Already exists: inspect first'; exit 1; }
cp "$HOME/.rovor-worker-smoke-state/com.rovor.ghost-worker.readonly.plist" "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.rovor.ghost-worker.readonly.plist"
launchctl print "gui/$(id -u)/com.rovor.ghost-worker.readonly"
```

Add a disposable job from a separate terminal; a future launch can process it:

```sh
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" enqueue --kind system.ping --key launchd-smoke-1
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" status
```

Inspect the local `launchd.out.log` and `launchd.err.log` in the state folder for evidence; also check the actual SQLite `succeeded` receipt. Launchd submission or a plist validation does **not** demonstrate that the job actually executed.

## Stop and completely disable

A persistent stop marker inhibits further job execution between tasks:

```sh
python3 tools/ghost_worker_loop.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" stop
```

To disable the scheduler, unload it and keep the original job receipts:

```sh
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.rovor.ghost-worker.readonly.plist"
```

Removing the copied plist from `~/Library/LaunchAgents` afterward is a separate **manual** choice. The generating file and SQLite state should not be silently deleted. `resume` clears STOP, but never starts a process by itself.

## Limits of the current proof

Offline Linux unit tests validate plist structure, bounds, idempotency and injection-resistant arguments; this is **not** a native launchd runtime test. On macOS, GUI apps and user LaunchAgents depend on an actual logged-in user context, system sleep/power settings, permissions and app-specific capabilities. `StartInterval` is not a guarantee of clock-exact execution or all-day operation during sleep. Verify the real Mac host, actual `launchctl` status, job receipts and interruption handling before extending access. Never put passwords, API tokens, business email contents or client assets in GitHub.
