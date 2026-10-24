# Paced research worker on the existing Mac service

This candidate replaces the existing scheduled tick, not the executor or SQLite
queue. The same `com.rovor.ghost-worker.readonly` LaunchAgent invokes
`omniroute_continuous.py` every 301 seconds. One tick admits at most one model
job. Atomic SQLite pacing requires at least **601 seconds between claims**,
with a ceiling of **144 claims per rolling day**. A five-minute schedule usually
previously underfilled the limit when 300-second ticks missed the 601-second boundary. The reviewed 301-second cadence permits the second subsequent tick (~602 seconds) to clear the minimum gate under ideal no-lag scheduling; actual launchd runtime and provider availability can still lower throughput.
Existing defaults remain unchanged unless continuous dispatch is explicitly
enabled. An actual provider's free quota can be lower than the local allowance.

## Work and replenishment

Each tick reads the fixed public GitHub repository's main ref and its exact
commit-pinned `coordination/tasks.json`, using bounded unauthenticated GETs.
Unfinished tasks can receive four distinct research deliverables: implementation
plan, acceptance checklist, failure scenarios, and handoff template. Each payload
is independently checked against that pinned public source before admission.
A changed main commit alone does not repeat an assignment; changes to its title,
acceptance or output form create new work. This is **research about** the shared
development tasks; it does not claim, modify or complete those GitHub tasks.

An offline fallback catalogue contains 168 distinct role/topic/output assignments
for Mike, Jane, Jesse, Gale, Gus, Saul and Hank. The existing queued recovery jobs
take precedence. Previously attempted IDs never replay. When both live tasks
and fallback assignments have been handled, the worker reports exhaustion and
keeps checking for new public work. It does not loop over identical prompts to
appear busy. Inference produces private drafts for human review; it does not
execute generated code or control Moho, Blender, Final Cut, email or social posts.

## Model and failure boundaries

The adapter reuses the existing `rovor-fast-free-v1` route verification, current
workpack source allowlist, Keychain lookup, loopback transport, 4096 completion
ceiling, visible-answer admission and private draft review. No new provider,
paid fallback or credential is installed. Public source text and the pinned
task title/acceptance are the only prompt inputs. The task is saved alongside
its source commit and receipt, with a hash binding the assignment manifest.

STOP is checked before queue admission and again before inference. A running
research job prevents a concurrent admission. All claimed attempts count toward
the rolling allowance. Three consecutive recorded failures pause claims; even
pre-inference failures are recorded for this circuit. The worker does not retry
an uncertain or failed ID. A pause or provider outage means it is not completing
work continuously; the schedule remains installed and status gives the reason.

## Activation

Use an immutable clean checkout of the tested candidate. The installer is a
dry run unless `--apply` is supplied:

```sh
python3 tools/install_continuous_worker.py --expected-commit FULL_COMMIT_SHA
python3 tools/install_continuous_worker.py --expected-commit FULL_COMMIT_SHA --apply
```

Apply checks the existing free-route/authentication preflight without requesting
a model completion, rejects an existing STOP or running job, holds the database
claim lock through service pause, backs up the original plist, then reloads the
same service label with its existing interpreter, state and workspace. Failed
activation restores the prior plist and service with STOP held. On success it
clears only its own rollout STOP and requests one scheduled tick. It does not
claim a model completed merely because launchd loaded the service.

Host activation must run on the actual Mac with permission to write its existing
LaunchAgents and private worker state. In the preparing ChatGPT session those
paths were readable but outside the permitted write roots, so **no host rollout
or new live model completion was performed**.

## Inspection

Read-only status from the installed candidate:

```sh
python3 tools/omniroute_continuous.py --state PRIVATE_STATE --workspace WORKSPACE --status
```

The worker also writes `continuous-status.json` in the private state directory.
It reports the tick time, source refresh, queue result, actual executed count,
review-ready flag and dispatch reason/next eligible time. Drafts and their
assignment manifests remain under the existing `omniroute-drafts/UUID/` tree.
These artifacts are not automatically published or approved.

## Validation and limits

Local Mac checks: 288 existing workforce tests, 15 new runtime tests, six
installer tests and 12 pacing/health tests. Concurrency, changed-source
replenishment, no duplicate work across unrelated main commits, forged source
rejection, STOP, quota, failure circuit, one-completion boundary, no replay,
same-service configuration and rollback are covered. Live provider completion,
background authentication after rollout and a real 24-hour soak still require
host verification. Offline simulations are not proof of unattended operation.
