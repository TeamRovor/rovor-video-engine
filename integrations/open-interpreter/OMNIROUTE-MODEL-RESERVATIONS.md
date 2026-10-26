# ROVOR OmniRoute — shared SQLite atomic model capacity

**Why:** The installed continuous Mac LaunchAgent already uses SQLite `BEGIN IMMEDIATE` to claim research jobs. A model selector alone cannot prevent two simultaneous consumers from using the same remaining provider allowance or all the available in-flight slots. This extension is the **reservation primitive** for that same worker — not a second worker or a new schedule.

## Contract

Call `omniroute_model_reservation.reserve(conn, job_id, task, models, now=..., stop_present=False, failure_circuit_open=False, host_evidence_authenticated=True)` **while the existing `ghost_worker.claim()` owns the SQLite `BEGIN IMMEDIATE` write transaction and BEFORE the same queued `research.omniroute` job is marked running and committed**. Do not call it after the job claim commits; separate transactions leave a double-booking window.

It checks actual queued `research.omniroute` job ID, refuses previously reserved job IDs, validates STOP and global circuit, applies the previously merged proportional-capacity selector, and records one model + shared provider/account quota-pool reservation in an additional table in that same SQLite DB. The helper never sends an inference POST or enqueues/retries anything. If the surrounding claim fails and rolls back, so does its reservation. `host_evidence_authenticated=True` is an API precondition **and not proof**; only the current on-Mac trusted caller with independent verified quota/cost/privacy/terms and usability evidence may supply it.

Model slots must include exact (not guessed) ID, verified capabilities, remaining quota and cooldown from PR #144 plus `quota_pool_id`, `pool_remaining_requests`, `pool_verified_at`, `pool_inflight`, `pool_max_inflight`. Multiple models sharing a provider/account must use the SAME sanitized pool ID and consistent pool evidence. This avoids a hidden issue in independent-per-model quota tracking: two models from one provider account can otherwise use the same last free request twice. If account resources/limits are unknown, they are unavailable.

The selector subtracts already recorded local reservations after the attested snapshot for **both** the model and its shared account/pool. It also checks local held slot counts. It selects a different eligible account/model for the NEXT new job if the preferred one is busy/exhausted. It does not replay the old failed job or assume a reset guarantees new capacity. At reset, the model only re-enters with a NEW authenticated snapshot showing usable quota and current terms. Failed/uncertain reservations do not expire automatically.

After the original job becomes terminal and verified (needs_review/succeeded/failed), call `release_finished_slot()` in a write transaction to free **in-flight concurrency only**. All reserved attempts remain permanently counted toward their previously observed quota windows until new trusted evidence supersedes them. No blind refund even if a failure happened before the POST.

## Existing runtime integration boundary (NOT YET APPLIED)

- `tools/ghost_worker.py` and `tools/omniroute_continuous.py` in PR #137 are owned by the existing Mac worker integration task. Do not change that owner scope or install this helper independently.
- Inside the same existing job-claim transaction, select+hold a reviewed exact model from this policy, then atomically attach its route identity to the same queued job. The existing workpack POST accepts an OmniRoute combo name, not an arbitrary selected provider/model ID: live integration **also needs an explicitly approved single-model route or verified model-to-combo translation, plus receipts recording the actual responding upstream model**. Never silently treat the pinned three-model fallback combo as proof nine endpoints are being used.
- Use one existing service, a single SQLite job queue and existing STOP/circuit, separate per-provider rate limits and shared pool quotas, and preserve aggregate owner-approved 144 claims/day / 601-second pacing until host-proven independent budgets justify a reviewed change.
- To maximize real throughput, feed the queue with finite, useful, properly sized and deduplicated tasks; do not simply mint endless placeholder research plans to spend free allotments. Distinguish drafts requiring review from human-accepted useful deliverables.
- Unit tests use temporary local SQLite files, fake model attestations, and two concurrent SQLite connections; they do not access the live Mac worker, provider credentials, or models. A passing test or merged source is NOT host deployment or nine models running.

Prerequisites: merged PR #141 (actual model fleet audit); merged PR #144 (proportional model selection); running PR #137 existing Mac LaunchAgent owner.
