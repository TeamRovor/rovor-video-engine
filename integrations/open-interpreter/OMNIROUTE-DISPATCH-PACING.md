# OmniRoute pacing and exact quota health

The Mac worker was configured for 14 claims per rolling 24 hours and spent
that allowance in an early burst. Failed attempts count too. Three recovery
assignments remained queued despite an installed, enabled LaunchAgent.

`tools/omniroute_dispatch_pacing.py` provides an independent decision function
and a read-only health command. It does not install pacing or increase limits:

```sh
python3 tools/omniroute_dispatch_pacing.py
```

The command reads the existing LaunchAgent's state path and quota, copies a
stable database/WAL snapshot to a temporary directory, and reports only counts
and fixed reason codes. SQLite opens the temporary copy, never the live files.
It does not call models, print private model text, mutate jobs, clear STOP, or
create a second service. Missing, changing or invalid evidence fails closed.

## Result on Amar's Mac

The read-only probe on October 24, 2026 observed 14/14 claims, 3 queued jobs,
0 running jobs and 1 consecutive recorded failure. The first quota slot
becomes eligible after **2026-10-25 00:06:10 UTC**, which is **October 24 at
7:06:10 p.m. America/Chicago**. The existing 300-second schedule can add delay.
This is quota eligibility, not a guarantee of a provider call or completion.
The probe explicitly reports `pacing_installed: false`.

## Required integration in the existing claim transaction

Call `dispatch_decision` after reading all recent claims while holding the
existing `BEGIN IMMEDIATE` transaction and before selecting/updating a job.
Passing a decision obtained outside that transaction permits a race and is
not sufficient. Keep existing free-route, STOP, source, review, no-replay and
provider guards. Do not interpret `allowed` as permission to bypass them.

Use `recommended_interval(max_claims)` or a longer explicit interval to spread
the budget through the full day. For example, 144 claims/day requires at least
601 seconds between admissions; a 300-second scheduled tick may reduce the
actual rate further. Current runtime validators accept at most 20, so **144 is
only a simulated example**, not an installed setting or authorization to spend.
Do not silently raise a configured limit or infer provider quota from it.

When blocked, the function differentiates `rolling_quota`, `paced_wait`,
`stop_requested`, `failure_circuit_requires_review`, `existing_work_running`,
and `no_queued_work`. Time-based waits include a safe next-eligible timestamp,
including the current executor's inclusive 24-hour lower boundary. STOP,
circuit, running-work and empty-queue states do not invent a wakeup time.

## Task supply is still a separate runtime requirement

The existing feeder has a finite allowlist. This change neither generates new
assignments nor repeats completed/failed work to simulate productivity. The
runtime owner must connect new distinct, approved work to that same queue and
expose exhausted backlog separately. Review-ready output does not mean a human
approved it. This module cannot establish continuous productive 24/7 operation.

## Validation

12 focused tests cover the observed 14/14 stall, excess claims, exact rolling
window boundaries, combined quota and pacing, seven simulated days at 14,
20 and 144 claims/day, STOP/circuit/running/empty queue, malformed timestamps,
live-WAL snapshot visibility, source-byte preservation, redaction and symlinks.
Local macOS tests and a read-only host probe passed; workflow results must be
checked independently. No additional live model completion was requested.
