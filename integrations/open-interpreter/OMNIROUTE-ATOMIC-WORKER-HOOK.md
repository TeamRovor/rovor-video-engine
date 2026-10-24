# ROVOR continuous OmniRoute worker: end-to-end atomic fleet dispatch candidate

**Branch based on active PR #137. Not installed on the Mac.** The already-running same-service LaunchAgent is unaffected. Running CLI with existing arguments uses exactly the old pinned-three-model free-only routing and the original global 601-second claim pace / 144-claim ceiling.

## What now works in the existing worker code path

An internal opt-in `omniroute_continuous.tick(..., verified_fleet_provider=trusted_host_function)` passes a trusted current per-task model/pool capacity snapshot to `ghost_worker.run_once(..., omni_verified_fleet=...)`. The existing `ghost_worker.claim()` takes the source-verified PR #146 model/pool slot reservation inside its preexisting `BEGIN IMMEDIATE` SQLite transaction, before atomically claiming the same queued job.

- Task UUID is bound to the exact job ID; only new queued `research.omniroute` jobs, never failed/replayed IDs.
- The selected model must match an **approved, visible single-model OmniRoute combo** with exactly one explicitly pinned provider/model and `:free` configuration. Multi-model fallback combo is refused because it cannot prove which model was selected. Account zero-cost must also be attested independently; the suffix is insufficient.
- The chosen model ID, provider, pool and combo are carried from the claimed job to `omniroute_continuous.execute()`. Immediately before gateway HTTP completion the live combo catalog is reread and verified again; a changed provider/model or fallback order blocks that assignment with **no POST**.
- A successful or review-required terminal draft releases per-model concurrency in the same DB while retaining its request against last verified quota. Unknown/failed/stranded reservations remain held pending review, not silently replayed/refunded. STOP and the existing three-failure circuit and 144/day + 601-sec global claim guards remain.
- No private model text/credentials are emitted to public GitHub or to continuous-status. The result only describes the **configured selected model**, not independent upstream response provenance or human-accepted useful work.

## Production deployment remains gated

A boolean `host_evidence_authenticated=True` or a locally edited JSON config is **not** proof of real account free eligibility, remaining upstream quota or successful model call. This branch deliberately has no public CLI flag for injection of arbitrary claims as verified capacity. Host operator needs a trusted authenticated provider/account adapter to supply a fresh max-15-minute model+shared-account capacity snapshot. The initial snapshot should be conservative (one in-flight/model); each model must have confirmed privacy/terms, `$0` billing and usable canary. Only specific provider-approved public research may run.

Integrate a validated Mac-only provider adapter with the internal callback after reading existing `tools/omniroute_model_fleet.py` on the same computer (note PR #141 on main is not automatically present on this PR #137 base). Existing ROVOR combos pin three OpenRouter models in overlapping multi-model configurations and therefore DO NOT currently satisfy the single-model binding requirement. Do not rearrange them automatically. The 9 OmniRoute provider connection entries have not been established as 9 eligible single-model routes.

**Do not reinstall or reapply the current active `b736610...` worker.** Test on a detached staging Mac candidate with separate private state and mocked providers. Only after hardening, test opt-in single-model routing and receipts with direct operator approval, then use the existing safe same-service rollforward/install procedure. Never create a second scheduler or expand spending/claim caps just to appear busy.

## Evidence

Tests use temporary SQLite and mock gateway only, including legacy fallback, exact model binding, rollback on route drift, one correct completion and reserved-slot release, no POST on drift after claim, and callback opt-in. Compare quality with useful human-approved drafts rather than the count of jobs tagged `needs_review`.
