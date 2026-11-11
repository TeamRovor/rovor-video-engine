# Ask ROVOR 2.0 — model intelligence registry, stage 1

Parent: [Issue #309](https://github.com/TeamRovor/rovor-video-engine/issues/309).

## What this change implements

`ask-rovor-model-registry.mjs` is a small **pure, read-only** module that represents all nine provider slots even when no usable models are known. It separates catalog discovery from admission, measured quality and manual/automatic selection. It adds a strict first-pass dispatcher **intent contract**, not a first-pass LLM call. It changes **no live HUD, private Site, worker endpoint, D1 schema, deployments, jobs, inference, GitHub permissions or Mac configuration**.

Model IDs reflect the current source-only Gemini catalog normalization (REST `models/foo` becomes OpenAI-compatible `foo`). This normalization does not grant eligibility or alter trusted server-side model pins.\n\nThe existing Ask ROVOR Smart route in `dashboard/command-center/native-v8-9/hud-chat.js` still uses legacy keyword heuristics. Nothing in this stage silently replaces or integrates that selector.

### Inputs and trust boundary

All data must be prepared **inside a trusted, authenticated server**. Never accept eligibility from a browser body, model-generated text, GitHub issue, page content or source excerpt.

- `catalogs`: entries `{provider, observed_at_ms, models:[{id,context_length?}]}`. Use exact IDs from a current fixed-provider catalog endpoint; presence alone is not inference proof.
- `admissions`: entries with `provider`, exact `model_id`, `dispatch_enabled`, `stop_requested`, `zero_cost`, `canary`, `quota`, optional `cooldown_until_ms`. A private server must validate current billing and authorizations **before** creating these records. Strings and booleans in a JSON receipt **do not independently prove** free billing or enforce provider quotas.
- `reviews`: owner-reviewed outcome receipts `{provider,model_id,task_family,outcome:'accepted'|'rejected',receipt_ref,finished_at_ms}`. Avoid model-assessed self-ratings. Unique review receipts only; no prompt/response contents.
- `now_ms`: injection of trusted server clock for testability.

The module discards unknown catalog fields, including anything that looks like a token or credential. It outputs only a bounded safe snapshot. It does not log or store raw prompts, API keys, billing evidence contents or private receipts.

### Admission requirements (all must pass)

1. Provider is one of the nine named sources and the **exact** model ID appears in a catalog no older than 30 minutes.
2. A unique private admission record explicitly has `dispatch_enabled: true` and `stop_requested: false`.
3. Current zero-cost evidence has a server-validated private evidence reference, verification age at most 24 hours and a short expiry. These fields are private operator inputs, **not** cryptographic verification performed by this module.
4. A real successful canary receipt identifies that exact resolved upstream model and is no older than 24 hours.
5. Provider/account-scoped quota evidence was observed within five minutes, has an explicit scope, a positive **request** allowance, and a future reset time. The production integration must additionally account for shared limits, RPM/TPM and atomic reservations before each inference call.
6. Any active/unknown cooldown or duplicate/conflicting admission blocks the route. Fail closed on unknown values; no paid fallback.

**Important:** This is a selection preview, not a dispatch authorization. The actual executor must re-check and atomically reserve quota immediately before each call; otherwise a previously eligible model could exceed allowance after the snapshot. The server must also verify the provider account's applicable commercial, training/data-use and free-tier conditions.

### Selection

`validateDispatcherIntent()` accepts only a strict object containing `schema_version`, `task_family`, `complexity` and `needs_review`. Any extra fields such as raw shell commands, arbitrary URLs, API keys, model requests or tool calls are rejected. The AI can describe a task, but cannot grant itself authority.

`selectModelRoutes()` is deterministic, bounded and read-only:

- Explicit/manual `{provider,model_id}` requests either select that *exact eligible* identity or return a block; no hidden substitution.
- Automatic selection considers only eligible models with an exact-ID advisory match or enough owner-reviewed evidence for that task. Otherwise it blocks instead of guessing a model alphabetically. A task-irrelevant model cannot be added merely to fill the optional second-review slot. Repeated owner-rejected outputs can downgrade editorial preferences. This does not claim measured superiority.
- Owner `accepted/rejected` quality metrics appear and influence ranking only after at least five distinct valid receipts for that task and model. Never infer quality from request share or mere completion.
- Optional review selects **at most two** models from different providers. No round robin or uncontrolled fan-out. Selecting a model does not execute it.
- When all providers are unverified, the correct result is `no_verified_eligible_models` and zero calls.

### Current provider hypotheses, not final ranking

The static advisory registry names selected exact model IDs seen in provider catalogs: Gemini Flash-Lite for classification, Groq GPT-OSS 20B for fast general work, Mistral Codestral and OpenRouter North Mini Code for engineering, Nemotron Ultra and GPT-OSS 120B for reasoning, Cohere Command for retrieval, SambaNova for alternative technical analysis, NVIDIA/Hugging Face candidate models for specialized work, and Cloudflare Workers AI for lightweight hosted tasks. This is **not** an account-active model roster. Availability and API terms can change; catalog discovery may show other models. Do not label these as the "best" until benchmarked on representative ROVOR tasks.

## Validation

```sh
node --check integrations/hud-cloud/ask-rovor-model-registry.mjs
node --test tests/test_ask_rovor_model_registry.mjs
```

Tests cover nine fixed provider slots, catalog-only denial, `:free` suffix non-authority, current evidence, redaction, stale/future proof, STOP, billing, canary identity, quota, cooldown, duplicate admissions, manual failure, independent review count, deduplicated PASS/FAIL metrics, deterministic task-aware choice, prototype-like catalog IDs, unrelated-task refusal, hostile intent fields and bounded inputs. These are **synthetic/offline tests**, not provider benchmark or production proof.

## Next integration PRs (separate scoped changes)

1. Implement an authenticated server adapter mapping **existing** provider inventories, private free-plan eligibility checks, actual canary receipts and scoped quota counters into this contract. Do not create another secret store, scheduler or D1 database.
2. Build a true first-message dispatcher behind the existing Ask ROVOR Cloudflare HUD using strict structured output, comparing Gemini Flash-Lite and Groq GPT-OSS 20B for classification accuracy and routing latency. Never accept tool execution instructions directly from model output.
3. Add reserve-and-revalidate at dispatch time, exact resolved-model receipts, STOP, bounded operations, cancellation and owner reviews; no Mac dependency or paid fallback.
4. Only then replace front-end keyword Smart route with server-selected routing and provide a polished mobile/desktop activity timeline. Keep the existing circular quota rings and preserve current auth, history, provider inspection, manual model selection and private sharing.
5. Require focused security/browser tests and owner PASS/FAIL before the existing private HUD production deployment. No auto-merge.
