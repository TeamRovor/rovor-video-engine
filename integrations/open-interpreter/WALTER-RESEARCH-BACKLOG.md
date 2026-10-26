# Walter: prepared public research backlog for ROVOR specialists

**Status: source release, not a running Mac AI employee.**

This is the non-overlapping piece of the unattended-worker problem: the existing active `ghost_omniroute_feed.py` work plan contains only a single one-shot task, then reports `plan_exhausted_review_required`. A working five-minute LaunchAgent cannot keep producing useful work if its approved catalog is empty.

This change stages **14 concrete public-source research assignments** in `coordination/walter-approved-research-backlog.json`: two each for Mike, Jane, Jesse, Gale, Gus, Saul and Hank. Each has an immutable ID and dedupe key, cited source paths, bounded question, expected deliverable and three acceptance conditions. Stage 1 covers each role once before stage 2. This backlog is deliberately finite. It prevents a model from inventing endless paid or unsafe tasks.

## Read-only validator and selection contract

`python3 tools/walter_research_backlog.py` performs offline release validation. The module's `select_next(...)` is an **integration helper**, not a direct queue writer or inference client. It returns one small `candidate_only_not_enqueued` item at most and only when **all** of the following are supplied by the trusted host caller:

- STOP is absent in the existing state folder, and no other STOP state is being ignored
- The actual existing SQLite dedupe ledger has been checked; prior **failed, in-review and succeeded** IDs are all considered used, with no replay
- The owner separately authorized model use on the existing local worker; a manifest checkbox is never model-use authorization
- The exact requested local OmniRoute model route has been checked for applicable free entitlement, account quota, privacy and commercial license
- The existing five-claim rolling 24-hour cap has remaining capacity; the existing worker must remain the authority for the actual claim transaction

No CLI path bypasses these checks to enqueue or run anything. There are no secrets, network requests, user data, model calls, file mutations or second schedulers in this new component. The existing repository development task queue is NOT used as a Mac runtime queue. Source inputs stay strictly within preselected public ROVOR files.

## What integration still requires

The Mac owner of active `omniroute-workforce-composite-20261023` exclusively owns `tools/ghost_omniroute_feed.py`, `tools/ghost_omniroute_job.py`, `tools/ghost_worker_loop.py`, `tools/omniroute_mac_schedule.py` and all Mac runtime changes. **Do not edit or deploy those files from this task.**

After that owner has repaired the observed HTTP 502 / empty-answer outcome and verified one new acceptable read-only OmniRoute response, it can review this exact release and integrate release items as additional separately authorized, durable public research packets. The existing low-level `omniroute_workpack_runner.PACKETS` and `ghost_omniroute_job.ROUTES` are allowlists: a candidate from this catalog is **not executable until explicitly registered and its correct source inputs, prompt boundaries and free-model route are validated**. That implementation must preserve the existing SQLite journal, STOP, one-job-per-tick behavior, rate gates and private receipts.

The existing single-job plan is not expanded by this PR. There is no claim of 14 AI jobs run, overnight productivity, full 24/7 availability, Final Cut/Moho/Blender access, Cloudflare deployment or failure repair. Use separately verified host receipts to make those claims.

## Verification

- `python3 tools/walter_research_backlog.py` validates all fixed public paths and release safety gates
- `python3 -m unittest discover -s tests -p test_walter_research_backlog.py -v` verifies two waves, unique IDs, successful first and exhausted last candidate, persistent no-retry semantics, STOP, authorization, free-only route, cap, path and source integrity constraints
- Workflow `.github/workflows/walter-research-backlog.yml` checks Python 3.9 and 3.11 without a provider connection

GitHub-hosted regression success proves source behavior only, not deployed Mac behavior.
