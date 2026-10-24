# ROVOR OmniRoute: proportional task routing + automatic eligible replacement

Owner goal: **keep all actual models productive to their verified usable capacity without overload or expense.**

## What is implemented

`tools/omniroute_capacity_router.py` is an **offline, inert selection policy** for the existing Mac OmniRoute worker. It is not a model, a ChatGPT worker, a scheduler, a second task queue, an inference caller or a replacement for PR #137.

Its `decide(task, slots, now=..., stop_requested=..., failure_circuit_open=...)` checks:

- Workload size and specialized skill requirements vs each model's verified tier/context/output limits; keep at least **20% token headroom**. If none fits, require splitting the assignment or a more capable approved model instead of sending a task that will truncate or fail.
- Per-model free account entitlement, exact approved model identity, public-data/privacy/terms authorization, zero cost, fresh (at most 15-minute-old) host attestation, confirmed quota, healthy provider and prior usable canary. A mere provider connection or `:free` suffix does **not** count.
- Independent quota remaining, next reset/cooldown, concurrent in-flight requests and empirically observed success rate. Select the **smallest capable** eligible model; prefer higher reliability before shaving latency. When occupied/exhausted, propose an alternate capable eligible model, never the same failed job ID. At reset/cooldown, the runtime must obtain **fresh quota evidence** before the original returns.
- STOP and the existing cross-model three-failure circuit remain global safety barriers. No paid/unknown provider or private client content is silently dispatched.

**This code does not change the installed worker.** Tests use invented model metadata only, no live model calls or claims. Choosing an ID never itself reserves a model, authorizes a real POST, raises quotas, or overrides STOP. Selection and reservation must occur atomically within the existing SQLite claim transaction.

## Production wiring that the current Mac runtime owner must own

1. Verify the **actual nine configured provider/model resources**, not eight worker characters, with the merged fleet inspector in PR #141. Classify models by context, reliable tasks, input/output capacity, free quota, reset time and allowed terms. Unknowns stay unavailable.
2. Bind authenticated provider evidence to each model ID; build task estimates and capabilities using real outcome measurements. Start with conservative tier ceilings. Keep all raw credentials, private data, and drafts local.
3. Use this policy inside the one existing PR #137 SQLite worker before each new claim. Atomically reserve a verified route/account budget and manage active model slots; fallback to **another eligible model for the next unclaimed task**, not retry already failed/reserved jobs. Wake on capacity refresh and at regular scheduler ticks.
4. On success update per-model tokens, latency, actual chosen upstream model ID, output validity and reviewed/accepted deliverable. On 429/quota/5xx/empty/length, cool down and reselect for fresh assignments only; do not bypass the global three-failure circuit.
5. Show real status in existing branded ROVOR HUD workload distribution: named employees, task queue, per-model configured/eligible/running/awaiting-reset, in-flight load, last accepted receipt, completion quality, health, remaining verified quota and next eligible time. Unknown cost/usage **must display unknown**, not zero or healthy.
6. Tune concurrency gradually using real provider limits (start at one in-flight per model), observe failure and useful-work rate, avoid saturation. Keep one runtime/LaunchAgent/SQLite. Do not raise the 144-claim budget or use nonzero-cost providers without explicit authorization.

## Important boundary

Existing PR #137 uses one global 601-second claim gap, and old workpack routes pin a **three-model OpenRouter subset**, not all nine connections. This policy alone cannot lift that global pace or magically reach the other six resources. Live multi-model parallel scheduling requires a reviewed host-side update with per-model pacing *and* a protective aggregate limit, cross-process locking, and successful Mac canaries. Until that occurs, the observed 22 claims are **not** 22 confirmed successful/accepted outputs.

Targets: existing continuous runtime PR #137, worker source PR #41, HUD fleet modules from PR #132, fleet inspector merged in PR #141.
