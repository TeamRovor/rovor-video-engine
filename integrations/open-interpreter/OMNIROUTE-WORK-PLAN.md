# Existing-worker work plan

The existing five-minute LaunchAgent can opt into `--approve-omniroute-work-plan`
alongside `--approve-omniroute-model-use`. The default remains no automatic
submission. There is no second scheduler or dependency installation.

`ghost_omniroute_feed.PLAN` is the finite reviewed release list. This release
contains one new `unattended-readiness` setup-acceptance packet, with fixed
public source inputs and the existing reason/free combo. It does not repeat
the earlier supervisor or overnight-checklist requests. The stable dedupe key
is independent of source changes: failures, completed drafts, restarts and
later code changes cannot resubmit that work. Existing running or queued
OmniRoute work takes priority. STOP blocks both submission and execution.

The existing queue still enforces five claimed AI jobs per rolling 24 hours,
one job per timer tick, exact free-route membership, private receipts and no
automatic AI retry. Receipt review does not establish factual correctness or
approve generated actions. Drafts remain `needs_review`.

Enable using `omniroute_mac_schedule.py --enable-approved-draft-queue
--enable-work-plan` only against its pinned runtime. It pauses and updates the
same existing service, requires the successful background-auth diagnostic,
proves STOP prevents execution, then resumes after verifying service load.
Do not repeat `--verify-background-access`: that diagnostic already exists.

When exhausted, the log reports `plan_exhausted_review_required`. The timer
continues, but no more AI requests are submitted. This is a finite feeder, not
an autonomous planner, web researcher, code executor or native-app operator.
Useful ongoing work requires additional reviewed non-overlapping packets and
adapters; never manufacture repeat work just to keep the process busy.

Source verification: 80 focused OmniRoute tests on actual Mac Python 3.9.6 and
pinned Python 3.12; 13 loop tests on Python 3.9.6. All inference was mocked.
The changed runtime has not yet been activated or tested with scheduled live
inference. The previously installed runtime remains the working host baseline.
