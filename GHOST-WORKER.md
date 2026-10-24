# ROVOR ghost worker — first executable slice (read-only)

**Status:** prototype code, not installed on Amar's Mac, Evan's Windows laptop, or the future PC. No unattended daemon, cloud-to-Mac bridge, AI model, email account, social account, Blender session, Moho session, or Final Cut Pro session is connected by this change.

This implementation adds a **local execution-job database** (`tools/ghost_worker.py`). It does not create an alternate owner/dependency database: `coordination/tasks.json` remains the sole GitHub development-task record. A local job is one invocation of a supported bounded adapter, not a GitHub development task.

## What it can execute today

- `system.ping`: a deterministic no-side-effect self-test.
- `files.inventory`: enumerate file paths and byte sizes inside an explicitly supplied local workspace. It does not read contents, move/delete files, open apps, or upload results. It rejects absolute/parent traversal, workspace escapes, symlink targets, and follows no directory symlinks. It enforces a maximum of 2,000 files and six directory levels.
- SQLite persists submitted jobs, stable deduplication keys, claims, bounded leases, attempts, results, and audit events between process invocations. Only read-only jobs can be retried after lease expiry; after two expired claims a job goes to `needs_review`. Failed executions do not silently retry.
- Single-step execution (`run-once`) requires an actual machine/process to invoke it. Simply storing this script in GitHub will not keep a computer awake or run it for hours.

## Mac or Windows local smoke test

After checking out the branch on a computer with Python 3.11+ (no package installs), pick an **authorized test directory** and a separate **private state path** outside the repo. Do not aim this early prototype at all of `~/` or at any client workspace.

```sh
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" init
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" enqueue --kind system.ping --key local-ping-1
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" run-once
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" enqueue --kind files.inventory --payload '{"subpath":"."}' --key downloads-inventory-1
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" run-once
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-test" --workspace "$HOME/Downloads" status
```

On Windows use `py -3`, with explicit Windows paths (`--state` and `--workspace`). The inventory result remains in local `jobs.sqlite3` and prints to the local terminal; it can contain sensitive **filenames**, so keep state private. Do not commit the SQLite database or raw inventories. Keep the state on a trusted local account; SQLite mode bits and an audit table are *not* a security boundary against a malicious local process.

Local validation in a checked-out tree:

```sh
python3 -m unittest discover -s tests -p test_ghost_worker.py -v
```

## What is deliberately disabled

These capability identifiers are declared but rejected before job insertion: `blender.scene`, `moho.animate`, `finalcut.timeline`, `email.read`, `email.send`, `social.publish`, `files.move`, `files.delete`. No credentials, OAuth scopes, private assets, application hooks, or accounts are assumed available. **There is no approval bypass:** side-effecting jobs cannot be submitted through the prototype. Human review of a proposed adapter and verified account/project-specific permissions are required before enabling an action.

Future adapters should specify: exact authorization boundaries, dry run, idempotency and duplicate prevention, timeout, rollback/compensation if applicable, receipt and external action ID, cancellation, account/tenant isolation, refresh-token storage outside GitHub, and clear reviewer approval for publishing/sending/deleting. A prompt claiming approval is not proof of authorization. For creative apps, run against disposable scenes before opening production projects. Re-check that externally visible actions were actually accepted by the provider rather than trusting the local process return code.

## Next proven milestone

Run the local smoke test on Amar's Mac; verify the SQLite receipts and an actual directory inventory. Then add an **explicitly approved, reversible file-move adapter** tested on a disposable directory, followed by read-only creative-software probes. Separately connect official social/email APIs with OAuth in a local secret store and require evidence of account ownership and publishing permission. Before enabling unattended scheduling (launchd/Task Scheduler), test restart recovery, crash mid-job, duplicate prevention, bounded resources and a working stop switch on the real host.
