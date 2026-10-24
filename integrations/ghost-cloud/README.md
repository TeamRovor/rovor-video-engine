# Nine-provider Mac-independent execution runtime

Implemented source, not deployed. Tests use real SQLite and mocked HTTPS
responses. No live model calls, cloud secrets, account billing checks, cloud
D1 binding, scheduler continuity, or nine-provider operation are implied.
This is the missing inference executor, separate from ChatGPT scheduled coding
shifts and from the Mac-local OmniRoute endpoint. It never calls Mac localhost.

The nine fixed adapters match the existing connection identities: Groq,
Gemini, Cloudflare AI, Mistral, NVIDIA, OpenRouter, SambaNova, Cohere, and
Hugging Face. Each has its own runtime secret and pinned model. No catalogue
model, API-key presence, or successful mock response authorizes live dispatch.

## Deployment and integration boundary

The existing private Site is `appgprj_6add1e2cc8c08191839344b34d7dbf50`.
Its HUD source/deployment is owned by `hud-persistent-telemetry-20261024`.
Do not create another HUD or overwrite its Worker, database, identity, audience,
or schema migrations. This directory is an independent module for that owner
to compose into the existing private Worker. Its `fetch` handles only
`/api/ghost/*`; its `scheduled` entry runs a bounded fleet tick. The deployment
owner must register an authenticated unattended invocation or supported cron;
an exported scheduled method alone does not register one on Sites.

1. Resolve the existing Site source-upload blocker. Its registered Git server
   was unavailable from the execution environment; version zero is unpublished.
2. Integrate the module and append `schema.sql` as a new migration in the same
   D1 database. Do not rewrite an applied migration. All tables are namespaced.
3. Provision distinct random reader/writer secrets of at least 32 characters
   through the host secret service, plus the nine provider secrets named in
   `runtime.mjs`. Cloudflare additionally needs `CLOUDFLARE_ACCOUNT_ID`.
   Never migrate raw keys through a public repository, browser bundle, URL,
   job body, automation prompt, logs, or GitHub Actions output.
4. Establish zero-cost account/model eligibility, applicable commercial terms,
   actual remaining quotas and one separately authorized real canary per model.
   Set `GHOST_FLEET_CONFIG` only from these operator-verified records. The
   booleans, digests and timestamps are **attestations, not authentication or
   independent billing verification**. Keep the underlying evidence private.
5. Enqueue bounded public-source tasks from the canonical shared queue using
   the existing coordinator's approved ownership. This ledger does not grant
   ownership, approve public source authenticity, replenish tasks, or accept
   model-generated commands. Provider output is a draft, never executable code.
6. Verify anonymous denial, writer/read separation, actual D1 persistence,
   live provider response/usage, STOP, quota exhaustion/recovery, overlapping
   wakeups and at least two independent scheduled executions with the Mac off.
   Integrate the authenticated status response into the existing HUD. Do not
   expose provider secrets or drafts in the public Pages completion feed.

The independent code can be released and tested before step one is resolved;
it cannot truthfully be reported as live or HUD-connected until these gates
have actual runtime evidence. Existing Mac worker services remain intact.

## Admission configuration

`GHOST_FLEET_CONFIG` is a private JSON object keyed by the nine provider IDs.
Absent/disabled entries cannot execute. Each enabled entry needs:

* `model`: exact operator-tested ID; no `auto` or `latest` aliases. OpenRouter
  requires an explicitly verified `:free` model and sends zero-price routing
  limits with fallback disabled. Hugging Face requires an explicit upstream
  suffix rather than its automatic provider selector.
* `pool`: normalized private shared-account identifier. Connections sharing
  account quota must have the same pool and identical account caps/spacing.
* `zero_cost`, `commercial_use`: true only after actual account/license checks.
* `evidence_sha256`, `verified_at`, `valid_until`: digest and epoch-millisecond
  bounds of current private eligibility evidence. Validity is at most 24 hours.
* `canary_sha256`, `canary_at`: digest/time of an independently verified
  successful real canary after that eligibility verification.
* `requests_per_day`, `tokens_per_day`, `min_interval_ms`: conservative account
  limits no larger than verified remaining provider allowance. Rolling local
  admission cannot measure unrelated usage of the same external account.
* `max_input_bytes` (up to 14,500), `max_output_tokens` (up to 2,400), `roles`
  (existing eight names) and `kinds` (`checklist`, `plan`, `code_review`,
  `research`): proportional task admission.

Eligibility renewal and live quota refresh are not implemented here. An
operator/verified adapter must refresh evidence; expiry stops new inference.
Do not extend timestamps just to keep the worker running. Unknown free-tier
status remains ineligible; this code cannot promise 24/7 free inference from
finite third-party quotas.

## Durable execution semantics

The D1 insert is one atomic admission/claim operation. A unique job ID can
produce only one attempt. Shared-account concurrency, spacing, rolling-day
request and conservative token reservations are checked in that same write.
Reservations use input UTF-8 bytes plus 256 message-overhead units and the
output cap; these are admission reservations, not measured token usage.
Global dispatch is capped at 144 attempts per rolling day. Three failures or
uncertain attempts in a pool since its last returned complete draft pause
that pool for operator review. Other eligible pools can take fresh jobs.

Each wakeup considers at most one job per eligible provider. It does not spin
idle requests. Expired running attempts become uncertain, never queued again.
Timeouts, malformed/oversized responses and unknown transport effects are
uncertain; empty, truncated and tool-call responses fail. No attempt is
automatically replayed. A failed job is kept for review; a replacement provider
gets a new job, preserving the original failed attempt. HTTP 429 cooldowns
honor `Retry-After` across all connections in that pool. STOP is persistent
and checked again before external requests; it cannot undo an in-flight call.

Successful text is stored as `needs_review`; `human_review` stays
`not_recorded`. Requested and returned model IDs remain separate. Missing
returned model/usage fields remain null. No tests, drafts, or timestamps imply
human acceptance, current online status, or measured billing.

## Authenticated endpoints

* Writer: `POST /api/ghost/control` with `{ "enabled": true | false }`.
  The database starts disabled. The reader cannot enable dispatch.
* Writer: `POST /api/ghost/jobs` with `id`, `employee`, canonical `task_id`,
  `kind`, public `title`, bounded public `prompt`, exact `source_commit` and
  `data_class: "public_repository"`. Matching duplicates are harmless;
  changed payloads under the same ID conflict. The trusted operator is
  responsible for truthful public classification and source/owner validation.
* Reader: `GET /api/ghost/status`: nine admission states and the latest 50
  factual job/provider/model/usage/status records. No prompts, output or keys.
  These records support the existing HUD; no UI file is replaced here.
* Reader: `GET /api/ghost/jobs/<id>`: the private draft and review state.

Bearer secrets remain server-side. A public browser cannot safely embed them;
the private Site's identity adapter must mediate HUD reads. This module does
not implement a second review ledger or change the existing PASS/FAIL owner.

## Verification

`node --test tests/test_ghost_cloud.mjs` requires Node 24 and no dependencies.
The tests exercise real SQL, mocked adapters for all nine endpoints, simultaneous
claims/ticks, STOP, per-pool/global budgets, cooldowns, circuit pauses, bounded
responses, immutable jobs, role/input admission, authentication and sanitized
HUD receipts. `.github/workflows/ghost-cloud.yml` runs the same checks without
any model credentials or live inference.

Official adapter references checked during implementation:

* https://console.groq.com/docs/api-reference
* https://ai.google.dev/gemini-api/docs/openai
* https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/
* https://docs.mistral.ai/api/endpoint/chat
* https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b-infer
* https://openrouter.ai/developers
* https://docs.sambanova.ai/docs/en/get-started/api-keys-urls
* https://docs.cohere.com/docs/compatibility-api
* https://huggingface.co/docs/inference-providers/index
