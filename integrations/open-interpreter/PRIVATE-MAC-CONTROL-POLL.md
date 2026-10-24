# Bounded private ROVOR control polling (foreground v1)

**Not installed on the Mac, not a background service, not native app control.** This is the private request-discovery layer for the reviewed one-job adapter (`ghost_private_control.py`), and continues to use the original `ghost_worker.py` SQLite execution engine. Never connect the privileged local worker to GitHub Actions in the **public** `rovor-video-engine` repository.

The *separate, active, private* `TeamRovor/<private-repo>` holds a single small `control/queue.json` on `main`:

```json
{"schema":1,"jobs":["mac-link-private-001"]}
```

Every ID in the queue refers to an exact `control/jobs/<ID>.json` packet (see `PRIVATE-MAC-CONTROL.md`). A Mac-scoped token in `ROVOR_PRIVATE_GITHUB_TOKEN` may read contents and write sanitized replies only to one locally chosen private issue. The remote queue cannot choose receipt issue, increase budgets, enable inventory, or supply shell arguments. Old completed IDs can remain in the queue without preventing later jobs: posted receipts are deduplicated by the existing per-ID SQLite state.

### Foreground trial, only after private repo and local access exist

From a reviewed, pinned checkout in a real authorized foreground Mac execution environment (not this GitHub-only chat):

```sh
python3 tools/ghost_private_control_loop.py --repo TeamRovor/PRIVATE-CONTROL-REPO --receipt-issue 1 --max-jobs 1 --max-seconds 900 --poll-seconds 90
```

The worker polls at most once every **60 seconds**, runs no more than **3 new task/receipt operations** per invocation, and ends within **one hour** even if no new work appears. Default is one new task per session. Its only tasks remain `system.ping` and, with separate local `--allow-inventory`, inventory of a newly isolated test sandbox. All instructions, filenames, paths, and identities are bounded by the existing adapter. No automatic installation/launchd, dynamic job creation, paid model, app edit, publishing, email, or arbitrary code from GitHub is introduced. To stop, place an ordinary `STOP` file under `~/Documents/Rovor/Mac-Control-State`; a symlinked or malformed STOP refuses service.

**Acceptance:** hosted tests demonstrate bad queue/public repo refusal, a safe one-job budget, time/interval bounds, STOP, no repeats and no starvation from old IDs. The first *real* successful private on-Mac execution and private issue receipt are separate required gates. Mac-local approval, credential storage (Keychain or another protected process environment), and optional bounded launch scheduling remain deliberately unimplemented until that host proof. This protects the user's laptop and preserves the user's existing Moho/Final Cut/art/media untouched.