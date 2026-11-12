# Mike — one-service continuous worker rollout review (public source only)

**Status:** Proposed host acceptance/rollback plan, **not** approval to activate. Prepared 2026-10-24 by the GitHub-only maintenance session for canonical task `a-overnight-02-mike-same-worker-rollout`. No Mac state, private receipts, credentials, or model requests were accessed. Do not interpret GitHub CI as installed-service evidence.

## Exact source and boundaries

- Candidate [PR #137](https://github.com/TeamRovor/rovor-video-engine/pull/137), reviewed head `c8510adb5534a2bb3304494ae43af8b84add3d85` (not merged into main at this review). Source: [installer](https://github.com/TeamRovor/rovor-video-engine/blob/c8510adb5534a2bb3304494ae43af8b84add3d85/tools/install_continuous_worker.py), [SQLite executor](https://github.com/TeamRovor/rovor-video-engine/blob/c8510adb5534a2bb3304494ae43af8b84add3d85/tools/ghost_worker.py), [continuous tick](https://github.com/TeamRovor/rovor-video-engine/blob/c8510adb5534a2bb3304494ae43af8b84add3d85/tools/omniroute_continuous.py), and [operator documentation](https://github.com/TeamRovor/rovor-video-engine/blob/c8510adb5534a2bb3304494ae43af8b84add3d85/integrations/open-interpreter/OMNIROUTE-CONTINUOUS.md).
- Existing service identity is `com.rovor.ghost-worker.readonly`. Candidate replaces its **single** LaunchAgent tick, not the SQLite executor, user account, provider route, or private state. `build_config` retains the installed interpreter, `--state`, `--workspace` and unrelated plist fields, and changes the command to `omniroute_continuous.py`, `StartInterval=301`, `RunAtLoad=True`, `KeepAlive=False`.
- The source enforces **at most one model job per tick**, **601 seconds minimum between claims**, **144 claims in a rolling 24 hours**, and a **three-consecutive-recorded-failure circuit**. These are upper bounds on *attempts*, not guarantees of model availability, useful drafts, or zero cost. The route `rovor-fast-free-v1` is a configured label, not proof of upstream free billing. The existing free-route/auth preflight is a necessary check, not permission to use paid inference.
- `seed` binds public work to a pinned GitHub source commit/assignment identity; it does not take over the GitHub development task claim. Private generated drafts remain review-only, and no failed/uncertain job ID may be automatically replayed.
- Do not edit PR #137's owned implementation, the overlapping PR #41 stack, the private database, or the existing service from this documentation task.

## Required owner gate before any Mac operation

Owner must separately approve the **specific reviewed commit**, intended free-only model route, allowable private data classification, host maintenance window and recovery operator. This document does **not** supply that approval. No second LaunchAgent, parallel scheduler, new provider, paid fallback, Final Cut import or automatic failed-job rerun is authorized.

Before considering a real rollout, an authorized Mac operator must independently confirm and privately record the following evidence (store no secrets or private state in this public repo):

| Gate | Acceptance evidence | Block / rollback trigger |
| --- | --- | --- |
| Immutable source | Exact full candidate commit matches reviewed PR head or a newly reviewed successor; clean checkout; relevant regression results pinned to it | Dirty/mismatched source, changed installer, or unreviewed PR head |
| Existing service | Exactly one expected user LaunchAgent label, existing executable and ordinary non-symlink plist; current `launchctl print` state; existing service's last healthy receipt | Missing/unexpected label, multiple active services, unverifiable baseline |
| Private state safety | Exact existing state/workspace paths and ownership/mode checked locally; private SQLite database and WAL/SHM backed up **consistently** to an owner-controlled private location, with restore procedure tested on a disposable copy | Backup absent, corrupted, wrong user, symlink redirection, or unsafe permissions |
| Active work and STOP | No `running` jobs/active leases; owner confirms no external STOP and no unresolved/manual-review jobs that require intervention; record baseline claim/receipt counts | Active lease, STOP already present, uncertain job state |
| Model and spend | Existing Keychain/loopback/free-route preflight succeeds **without completion**; provider billing/quota is independently confirmed $0-eligible for intended model and account | Any unknown charge, unavailable free route, paid fallback or failed auth |
| Limits and failure circuit | Verified proposed `301`-second schedule, `601`-second minimum spacing, `144` rolling-day cap, one-completion boundary, and three-failure pause; pre-existing claim history retained | Rate limit bypass, counter reset, second scheduler, automatic replay |
| Approval | Explicit human approval for maintenance/rollback, with an operator able to stop and inspect the real host | No authorized host operator or rollback ownership |

**Important implementation gap in the plan:** `install_continuous_worker.py` creates a private **plist backup** (`.before-continuous-<uuid>`), but does **not** create a SQLite database backup. An operator-owned consistent private SQLite backup is therefore a separate prerequisite; never copy raw DB files into GitHub. Also do not infer that merely observing no `running` rows proves all outstanding leases or private review work are safe: reconcile statuses and queue history locally before approval.

## Bounded activation sequence (operator only; not executed)

1. Capture read-only baseline: pinned source SHA, installed label/args/interval, service presence, state permissions, queue statuses/active leases, STOP presence, last heartbeat, model route, private receipts and rolling claim history. Preserve existing jobs and drafts. Check that the actual installer `build_config` accepts the current installed executor (legacy `ghost_worker_loop.py` or already-upgraded `omniroute_continuous.py`).
2. Obtain owner authorization and make a **consistent private SQLite backup** while respecting the current service's concurrency/transaction rules. Preserve existing private drafts and receipts. Confirm how to restore both service and DB if needed; do not clear STOP as a troubleshooting shortcut.
3. Run the documented installer **dry-run first** from the immutable clean candidate, with exact `--expected-commit`. A dry-run must report `model_requests: 0`, `state_modified: false`. Do not treat this as an installed-service test.
4. Only after all gates pass, an authorized Mac operator may choose the documented `--apply` action. Source `activate` creates a unique STOP token, obtains a SQLite `BEGIN IMMEDIATE` claim lock through `launchctl bootout`, backs up the original plist, writes the candidate, bootstraps **the same label**, and verifies service presence. It clears only the STOP token it owns on successful activation. A failed activation attempts original-plist/service restoration **with STOP held**. Do not erase a pre-existing or externally changed STOP.
5. Inspect the real service and `continuous-status.json` without exposing private draft contents. Confirm the new command and single label, heartbeat and queue transitions, one new unique claim (if any), actual completion/receipt status, review-ready flag, dispatch gate and next eligible time. A successful `launchctl print` or `kickstart` is **not** model completion.
6. Conduct an owner-observed soak over a meaningful window (ideally 24 hours), verifying claim spacing, rolling ceiling, STOP and failure circuit, private receipt retention, no repeated failed IDs, and no extra LaunchAgent. If provider quota/billing cannot be independently verified, **do not request inference**.

## Negative acceptance cases — proposed tests, not run here

| Scenario | Expected safe behavior |
| --- | --- |
| Existing STOP file, including symlink | Installer refuses activation; STOP remains; no service change |
| Job becomes `running` between baseline and pause | Locked recheck refuses rollout; no new job claim slips through |
| Unexpected plist label/executable, repeated/missing `--state` | Configuration rejected before change |
| Dirty checkout or mismatched `--expected-commit` | Refuse before modifying plist/state |
| Failed `launchctl bootout`, `bootstrap`, or service presence check | Fail closed; preserve STOP, restore original plist/service when possible; operator verifies actual restoration |
| STOP token replaced during rollout | Do not remove another actor's STOP; fail closed |
| SQLite backup unavailable or WAL/SHM inconsistent | Owner gate blocks; installer alone does not satisfy DB backup requirement |
| Pre-existing queued/review-required/failed IDs | Preserve identities and receipts; never replay failures or auto-approve drafts |
| Claim before 601 seconds, 145th claim in rolling day, or 3 recorded failures | Atomic dispatch denies new claim; no manual quota reset |
| Free-route preflight unavailable, unexpected model ID, chargeable route | No inference; preserve existing service and private state |
| No new receipt after successful launchd load | Report `receipt_pending`/blocked; do not claim worker success |
| Rollback after a partial activation | Hold STOP, reconcile active leases, restore exact prior plist/service; only restore DB from verified private backup when necessary and safe; human verifies |

## Evidence handoff template (fill only with real host observations)

- Owner authorization / operator / observation time: **NOT PROVIDED**.
- Candidate commit and exact clean-checkout verification: source reviewed at `c8510adb5534a2bb3304494ae43af8b84add3d85`; **host NOT VERIFIED**.
- Old/new LaunchAgent identity and service presence: **NOT VERIFIED**.
- SQLite backup consistency, active leases, STOP owner, private receipt baseline: **NOT VERIFIED**.
- Free-only upstream billing/quota and model-route preflight: **NOT VERIFIED**.
- Dry-run output / activation output / actual rollback test: **NOT RUN**.
- First unique real completion, receipt hash, human review-ready status: **NOT VERIFIED**.
- 24-hour soak / per-claim spacing / three-failure circuit: **NOT RUN**.
- Next action: owner reviews this public plan and the actual PR #137 source/tests; only an explicitly authorized Mac operator may perform the separate host gates. Report a blocker, not success, if any gate cannot be evidenced.

**Source-only outcome:** The reviewed code has a same-service, STOP-protected migration mechanism and explicit pacing controls. This document defines additional acceptance and recovery evidence; it does not change that mechanism, establish host readiness, approve inference, or deploy anything.
