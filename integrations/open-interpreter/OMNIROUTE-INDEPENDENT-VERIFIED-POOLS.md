# ROVOR independent verified-model pool admission — source integration

**This is NOT installed on the user's Mac and DOES NOT prove nine active AI models.** The user's real OmniRoute audit showed nine configured provider connection entries but only three different ROVOR-routed model IDs. Current installed LaunchAgent is still the older one-service pinned continuous build. This policy must not silently change it.

## Why this implementation exists

Original global dispatch denies every next job until a single 601-second cooldown elapses, and rejects any concurrent OmniRoute job as soon as *any* one job is running. Even separate eligible free accounts therefore idle. The Oct 24 PR #158 schedule alignment fixes a distinct issue (300-second launchd checks missing the 601-second window), but cannot fix this global serialization.

**New opt-in internal API:** the same existing `omniroute_continuous.tick(..., verified_fleet_provider=trusted_host_callback, max_verified_jobs_per_tick=1..9)`. Default `max_verified_jobs_per_tick=1` and no callback retain *unchanged* legacy global spacing. The current CLI has no override to spoof verified evidence. A count above one requires a callback independently verifying zero-cost entitlement, real account ID/pool, exact model, approved single-model route, capability and fresh quota. The callback returns a fleet packet including `host_evidence_authenticated=True`, `independent_pool_limits=True`, verified `models`, `routes`, `catalog` and a `task` bound to the exact queued UUID. Boolean fields are preconditions **not proof of authenticity**. The actual trusted adapter is NOT implemented or deployed: do not activate from manually edited JSON.

Each entry in `models` must contain the pre-existing capacity and shared-quota fields (PRs #144/#146) plus:
- `pool_min_interval_seconds`: authenticated minimum spacing for the **entire provider/account quota pool**, int 1..86400.
- `pool_max_claims_24h`: independently verified cap for that shared account, int 1..144.
- `model_min_interval_seconds`: authenticated minimum spacing for the chosen model, int 1..86400.
- `model_max_claims_24h`: independently verified cap for that model, int 1..144.

All models sharing a pool must expose consistent `pool_min_interval_seconds`, `pool_max_claims_24h`, remaining quota and snapshot age; conflicting snapshots are blocked. Model and account rolling windows count the *previous reserved attempts* in SQLite, not just successful replies. Finished/failed attempts are **never refunded or automatically retried**. The existing `BEGIN IMMEDIATE` serializes eligibility decisions and reservations, so two simultaneous workers cannot consume the same final verified account allowance.

For this explicitly verified mode only, `ghost_worker.claim` retains the **global 144-claims/rolling-24h emergency ceiling**, STOP, 3 consecutive failure circuit, exact queued-job UUID selection and per-call approval; it replaces global 601s/whether any job is running with the checked per-pool and per-model quotas and concurrency. If the account is exhausted, a separate eligible pool may receive a **new** queued job immediately. Lack of attested rate fields or no eligible models causes no inference/claim. An exact pinned `:free` model string alone is not zero-cost billing proof.

The opt-in `max_verified_jobs_per_tick>1` loops over at most nine unique queued items **within the same existing Mac LaunchAgent tick**. After each completed item it reads STOP again and obtains new host-attested model/pool evidence before the next SQLite claim. This is bounded *sequential* batching, not simultaneous nine-model GPU work; separate invocations may compete safely through SQLite and model reservations. Existing queued jobs are consumed first; public-source feeder may add one next deduplicated assignment between successes. The heartbeat reports bounded batch counts and uses a separate independent-pool reason rather than falsely reporting `paced_wait` from the old global logic. Raw draft text, credentials, private output and speculative model-success claims are excluded.

## Activation boundary

This branch contains **source and offline tests**, not an installed host adapter. The installed ROVOR Mac service is not changed. A full supported rollout needs actual host provider/account budget evidence and honest usable single-model canaries, the already existing PR #147 exact-route checks, one-service safe staging, explicit owner-approved deployment and measured fresh private receipts. Do not create nine fake workers, a second LaunchAgent, remove STOP/circuit, reset quotas, increase the global emergency cap, use unrestricted paid `auto` routes, replay historical jobs or automatically publish outputs.

Tests on Python 3.9/3.11 under macOS+Ubuntu verify same-second different-account admission; same-account blocks; old legacy cooldown unchanged; per-model/account pacing and 24h quota; retained global 144 cap and three-failure circuit; STOP midbatch; no manually injected unverified batch; bounded at-most-nine; source and receipt safety.
