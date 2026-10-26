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

## Private Site service endpoint authentication (P0)

The original owner's Site has a platform-service `POST /api/ghost/service`
operation supporting `status`, `inventory`, and `shift`. It must **never**
be an anonymous public shift trigger. The Site's shared operation adapter now
rejects the request with HTTP 401 **before** body parsing, database reads, task
replenishment, or provider calls unless the caller supplies

`Authorization: Bearer <private service credential>`

and the private Site host provides `GHOST_SERVICE_TOKEN`. Provision a new
cryptographically random secret of at least 32 characters on the host, **not**
in GitHub, browser HTML/JavaScript, job bodies, URLs, screenshots, command-line
history, or the public Pages HUD. The service secret must differ from the
`GHOST_READER_TOKEN` and `GHOST_WRITER_TOKEN`; reusing either fails closed.
Pass the service bearer credential only from the trusted private service
caller. Other owner-authenticated MCP actions retain their existing owner
identity checks. The service route never accepts owner-identity headers as
a substitute for this separate machine credential and never accepts a
`review` service operation.

**Compatibility requirement:** Existing platform callers of this route must
be updated to supply the dedicated secret before publishing the new source.
Do not disable authentication to restore an old caller. A cron `scheduled()`
hook runs locally without this HTTP service endpoint. After private Site
deployment, verify anonymous and reader-token POSTs return 401, a valid
service-token `status` succeeds, owner-only review stays restricted, and the
registered cron can execute without an exposed public trigger. These are
deployment acceptance tests, not evidence they have already passed live.

## Immutable review migration gate (P1)

The owner-private `/api/ghost/review` endpoint relies on `ON CONFLICT(attempt_id)`.
A legacy composer-generated `ghost_cloud_reviews` table omitted the unique index;
that schema can reject every review with a SQL conflict-target error. Fresh
compositions now declare `attempt_id UNIQUE`. **Do not edit migrations already
applied to a deployed D1 database** or claim an existing Site is fixed merely
by merging this source change.

For an existing database, before enabling PASS/FAIL, query privately:

```sql
SELECT attempt_id, COUNT(*) AS decisions
FROM ghost_cloud_reviews
GROUP BY attempt_id HAVING COUNT(*) > 1;
```

If any rows exist, stop: the owner must reconcile those conflicting historical
decisions with their original outputs before proceeding. Never auto-delete or
silently select one verdict. When there are no duplicates, **append** the SQL
from `migrations/owner-review-one-decision.sql` as a new, journaled migration
for the *existing* private Site, apply it to that D1 database, and verify
`PRAGMA index_list('ghost_cloud_reviews')` and an authenticated owner browser
PASS followed by an opposing FAIL returns 409 with only one unchanged record.
Do not apply SQL through a public GitHub Action, store review outputs in the
public repo, or overwrite an old migration file. Source/SQLite tests are not
proof the private Site is migrated or deployed.

## Scheduled shift to immutable approved-task feed

The source-only `compose-scheduled-shift.mjs` now bundles the already-reviewed
`approved-feed.mjs` with the **existing** owner-private Site deployment. A
scheduled shift uses the pinned canonical GitHub queue rather than the original
fixed `GHOST_APPROVED_JOBS` cache only when both the private Site opt-in and
feed configuration are present:

- `GHOST_CRON_OPT_IN=owner-approved-ghost-cron-v1` gates scheduled executions;
  it does **not** register a trigger.
- `GHOST_FEED_COMMIT` must be the exact immutable 40-character commit SHA for
  `coordination/tasks.json` and `coordination/work-routing.json`.
- `GHOST_APPROVED_TASKS` is a **private** JSON allowlist of at most nine
  `{\"task_id\":\"...\",\"revision\":\"v1\"}` entries. The canonical task
  must independently have `cloud_inference.approved_for_cloud=true`, status
  `active`, public data class, assigned owner, passing dependencies, and matching
  revision. There is no inferred authorization from a GitHub task alone.

When `GHOST_FEED_COMMIT` is present but allowlist data are missing or invalid,
the shift fails closed with a sanitized receipt; it must **not** fall back to
stale packets. If the feed is not selected, legacy fixed packets remain the
existing guarded behavior. Identical tasks deduplicate by stable job IDs; an
explicitly reviewed new revision requires new owner approval. The zero-cost
provider gate, token permits, global STOP, human PASS/FAIL, and real model
receipts remain separate.

The same `compose-scheduled-shift.mjs EXISTING_SITE --apply` command now
stages **both** forward-only D1 migrations in the original Site's journal:
first `cloud_review_one_decision` (only if not already journaled), then
`cloud_scheduled_shift`. It preserves all existing migration entries and
creates one combined staged Worker source/build. Run it without `--apply`
first to inspect the dry-run report; it never publishes or registers a cron.
It refuses unexpected Site IDs, changed bundles, symlinks, or repeat composition.
**Before publishing**, query the actual owner-private D1 for duplicate
`ghost_cloud_reviews.attempt_id` values as specified above and stop if any
are found. Applying a unique index to duplicate records must fail rather than
silently discard contradictory owner decisions. The original Site's publish
review must also account for the fact that database migrations may persist
even if publishing the updated code fails.

**Operational acceptance remains outstanding:** inspect the existing private D1
duplicate count, publish the updated original Site after reviewing the staged
migrations and original worker code, configure the private canonical allowlist,
register an actual hosting schedule, verify two independent scheduler wakeups
and one new approved and non-duplicate real attempt, and verify that human
review persists. Merging source is not deployment, and a scheduler heartbeat
is not proof of live model activity.

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
