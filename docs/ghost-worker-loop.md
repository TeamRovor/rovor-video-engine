# ROVOR ghost worker: bounded polling loop (prototype)

**Stage:** repository implementation and offline test only. This is **not** installed or started on either owner's actual computer and is not a Mac login agent. It cannot access Blender, Moho, Final Cut, email, social platforms, or private data unless a human explicitly points its **read-only inventory** at an authorized local workspace. No service, model, credentials or account access are installed.

## Relationship to existing files

- `tools/ghost_worker.py` (base PR #32) owns the *local* SQLite execution-job database, fixed allowlist (`system.ping`, `files.inventory`), deduplication and read-only lease recovery.
- **New:** `tools/ghost_worker_loop.py` opens the same database and calls that worker repeatedly. It does not create a second schema, reimplement job claims or widen the allowlist.
- `coordination/tasks.json` is the **GitHub development-task** ownership record, not the database for runtime jobs. A local job receipt does not confer GitHub ownership or approval.

## Foreground smoke test on Mac or Windows

From a working checkout containing **both PR #32 and this stacked branch** (Python 3.11+, no third-party modules), make a *disposable* workspace:

```sh
mkdir -p "$HOME/rovor-worker-smoke"
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" init
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" enqueue --kind system.ping --key smoke-ping-1
python3 tools/ghost_worker_loop.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" run --max-jobs 1 --max-seconds 30 --poll-seconds 1
python3 tools/ghost_worker.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" status
```

To exercise a bounded idle loop, choose `--max-seconds 20 --max-jobs 3`. It sleeps between empty-queue polls rather than continuously spinning. Stop it from a *second* terminal while it's running:

```sh
python3 tools/ghost_worker_loop.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" stop
```

The stop signal persists on disk; the process sees it **between** jobs/polls. Before the next manual run, clear it explicitly:

```sh
python3 tools/ghost_worker_loop.py --state "$HOME/.rovor-worker-smoke-state" --workspace "$HOME/rovor-worker-smoke" resume
```

`resume` never launches a process and never requeues failed jobs. Poll limits: 1–1,000 attempted jobs and at most 3,600 seconds **per invocation**, with polling every 0.1–30 seconds. Duration is cooperative; it does **not** preempt an already executing synchronous adapter. Always verify the job receipt and exact machine before claiming real host success.

Windows use `py -3` in place of `python3`, with explicit `--state` and `--workspace` paths. Avoid all of `~/`, your actual Desktop/Downloads, private customer folders and production artwork for initial testing. SQLite records paths in inventories, so keep state directories private and out of GitHub.

## Safety and next tests

- This is a **manual foreground command**. No service/autostart/launchd/Task Scheduler configuration is added.
- A persistent `STOP` file is the operator-controlled kill switch **between jobs**. Invalid/symlink markers fail closed.
- Two pollers may operate against the same SQLite database; the existing `BEGIN IMMEDIATE` claim prevents both claiming the same queued job. Each worker has a distinct `--worker-id`. No malicious-process sandbox is claimed.
- If a process dies after claiming a read-only job, the **base worker** requeues on lease expiry up to two attempts. No automatic replay of email, social, filesystem mutations or creative project saves is allowed.
- No tokens, credentials, social posts, emails, file moves, app control or shell commands are authorized by this addition.
- Validate offline with `python3 -m unittest discover -s tests -p 'test_ghost_worker*.py' -v`; verify on **actual Mac** before enabling a bounded launchd job. Future stages require crash/cancellation checks, OS login/session behavior, power/sleep handling, separate app permissions and explicit approval policies.
