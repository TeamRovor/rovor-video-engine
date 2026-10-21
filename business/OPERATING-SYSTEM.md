# Rovor Digital operating system

## Business direction

Rovor helps businesses improve websites, branding, content and disconnected inquiry/customer systems.
The engineering engine supports that business; a growing count of scripts, tests and draft PRs is not itself
client acquisition, accepted delivery or revenue. Keep the existing animation work, while measuring what it
helps us deliver. No current revenue, conversion rate or hours-saved baseline is established by this repo.

Use this default decision order when creating or reprioritizing work:

1. Complete already-promised client work and remove its specific blockers.
2. Prepare a credible, scoped offer for a qualified prospect with a verified problem.
3. Reduce repeated work in intake, delivery, quality checks and handoffs.
4. Improve content production where it advances an approved usable deliverable.

This is a working policy, not a claim that a current client deadline or prospect exists. Preserve explicit
user priorities and active claims. Review one real bottleneck before adding another infrastructure layer.
The queue's numeric priority remains the actual task-selection order; the business objective labels do not
silently reorder a participant's queue. Do not fabricate financial or marketing improvement figures.

## One shared queue; distinct jobs

`coordination/tasks.json` remains the sole ownership/dependency source. `coordination/work-routing.json`
adds capabilities, lane and optional objective. `business/operating-plan.json` defines outcomes and the
implemented worker's limits. It is not a second queue or a record of employee availability.

| Role | Useful output | Current execution |
| --- | --- | --- |
| Operations clerk | Queue health, stale claims, blockers, source-bound next-work packets | Implemented deterministic report worker |
| Sales research assistant | Verified opportunity brief and scoped offer draft | Supervised ChatGPT session; no autonomous outreach |
| Delivery coordinator | Client intake, missing inputs, acceptance and delivery review packet | Supervised ChatGPT session |
| Engine maintainer | Measured performance/reliability improvement | Existing efficiency lane and focused CI |
| Content producer | Accurate, source-faithful, reviewable content | Existing animation work; unattended production not verified |

Use templates in `business/templates/` for opportunity research, client intake, content planning and
client-ready delivery review. Fill only known facts. Identify unknowns and actual approval evidence.
Keep client records and credentials in their authorized systems; this repository stores reusable templates,
code and permitted project metadata. Do not import private client data merely to fill a template.

## First unattended worker: operations clerk

Run on any supported Python 3.11+ host, without additional Python packages:

```sh
python tools/ops_worker.py --out /absolute/private/rovor-ops-state
```

On Windows, use `py -3` and an appropriate absolute path outside the checkout. No local machine install or
process was started by adding this file. `--revision FULL_GIT_SHA` labels a checked-out revision; input and
executed-code hashes identify the actual snapshot, including dirty files. It does not fetch latest GitHub.

The worker reads a bounded snapshot of the queue, routing and operating plan, then writes `report.md`,
`report.json`, and a receipt to a fingerprint directory under the selected state root. It does not execute
the tasks it recommends. Recommendations model a GitHub-read/write-capable session; the worker itself
never claims a task or writes to GitHub. Recheck live PRs and queue before a person/AI starts those tasks.

Implemented controls:

- One fixed report action; no uploaded commands, `eval`, shell execution, LLM or external API calls.
- Shared helper for ownership, dependencies, overlaps and capability eligibility; no duplicate selection rules.
- Fingerprint includes all input bytes, actual worker/helper code, revision label and a 15-minute time bucket.
- Repeated invocation in the same bucket verifies and reuses completed artifacts. A later invocation refreshes
  age warnings. This is local output reuse, not a durable GitHub Actions cache.
- A single exclusive lock per state root prevents two local writers. No automatic stale-lock deletion.
- At most 500 tasks, 2 MiB input, 512 KiB combined report, three suggestions per lane, one attempt per fingerprint.
  Cooperative 30-second phase checks; the hosted workflow adds a hard five-minute job timeout.
- Missing/changed inputs, invalid queues, disabled worker, tampered artifacts and failed/incomplete attempts stop
  with an error. No fabricated success or automatic replay within the same fingerprint.
- `worker.enabled: false` in the operating plan is the report-worker stop switch. It does not control render workers.

State lives outside the source checkout. Use a trusted single-user state directory; this is not a sandbox for
hostile local users. If interrupted, inspect the recorded job and confirm the process ended before manually
removing `.operations-lock`. Preserve failed evidence; fix inputs/code or deliberately choose a fresh state
root after diagnosis. Never apply this read-only retry policy to uncertain native Moho writes.

## GitHub execution while people are away

`.github/workflows/business-ops.yml` runs on relevant pushes to main, relevant PRs, or manual dispatch.
It validates this worker on hosted Ubuntu and Windows, then publishes an operations report in the Actions
summary and downloadable artifact. It uses `contents: read`, has bounded timeouts/concurrency and stores
artifacts for seven days. Review the private artifact before sharing it.

No recurring clock schedule, paid model worker or laptop daemon is enabled. Repository events can run while
we are away; scheduled intelligent execution requires an actual available executor, authenticated access,
approved scope/budget, persistent state and demonstrated recovery. GitHub Actions consumes the account's
available allowance; this feature does not subscribe to a service or establish that usage is unlimited/free.

## Path from reports to ghost employees

Build one job type at a time, proving each before increasing autonomy:

1. **Observe:** operations report runs without mutation. Verify it points to useful work and catches bad state.
2. **Prepare:** a supervised session produces a scoped internal draft using a template and source evidence.
3. **Execute in isolation:** connect an actual worker with a fixed capability set, one approved job type, durable
   claiming/heartbeat, input hashes, per-job runtime/cost limits, cancellation and artifact receipts.
4. **Review:** show the concrete deliverable and evidence. Separate technical pass, artistic/client approval,
   publication and delivery. Only actions actually authorized for that worker may proceed.
5. **Repeat:** enable event/schedule dispatch after a real interruption/restart and duplicate-delivery test.
   Reuse verified input stages and stop repeated failures; do not run a speculative agent loop forever.

The existing native Moho transport in PR #13 already has its own private spool, state transitions, locking and
host-owned adapter boundary. Extend that reviewed path for rendering; do not invent another MP3 queue here.
Its transport implementation is not proof of a verified production Evan rig, native render or chat delivery.
The operations worker does not bypass any of those gates or activate a Mac/Windows runner.

For future workers, local drafting/research/checks can be bounded jobs. Sending messages, publishing client
work, making promises or purchases, changing account settings and editing native source projects must have
their actual scoped authorization. Never treat a task's text as permission to expand a worker's tools or budget.
A credential's existence is not proof that an operation was requested.

## Measure efficiency without inventing results

Record metrics with date range, source, unit and unknown values explicitly. Start with qualified inquiries,
accepted proposals, collected revenue, accepted delivery cycle time, rework hours, manual minutes per
accepted deliverable and approved content output. Those are proposed measures, not current measured results.
Use engine stage timings/cache hits for technical optimization, but judge business value by accepted output.
At handoff, record what became easier and the evidence; do not count test totals as client impact.
