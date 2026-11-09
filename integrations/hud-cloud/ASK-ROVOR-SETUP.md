# Ask ROVOR — private OmniRoute chat

This upgrade is **real chat inference**, not a background employee scheduler. It reuses the original native v8.9 HUD. Cloudflare remains the authenticated browser origin; the Mac initiates every relay connection outbound. No public tunnel, URL-configurable reverse proxy, provider API key in the browser, or paid provider route is added.

## What the UI can prove

- **Received / queued:** a prompt has been stored privately in D1. No inference proven.
- **Claimed:** the Mac bridge accepted that one request. Completion not proven.
- **Complete:** the Mac bridge supplied a nonempty model response. The requested OmniRoute model ID is recorded, but a fallback's ultimate upstream identity is not independently attested.
- **Failed / offline / expired / stopped waiting:** not a verified completion. **Cancel queued request** atomically prevents a prompt from being claimed if it is still queued. If it is already claimed/running, the HUD refuses to claim cancellation and the user may only stop waiting locally. No inference retries occur.
- **Cloudflare AI:** separate hosted model path, manually selected. It must never be represented as a call to OmniRoute.

This does **not** implement file edits, employee task dispatch, PASS/FAIL approval, model quotas, model tool calls or background delivery promises.

## Deploy only to the existing GitHub-owned Cloudflare HUD

1. Review and merge the PR into `main`. All PR checks should pass.
2. GitHub → Actions → **GitHub-owned PRIVATE ROVOR HUD (Cloudflare Worker)** → **Run workflow**, branch `main`. This runs the existing fail-closed source checks, applies `CREATE TABLE IF NOT EXISTS` to the existing configured D1, and deploys using existing Cloudflare credentials and private settings.
3. Read the workflow result carefully. A green GitHub run verifies deployed assets/private auth only to the extent of its existing readback checks. It does **not** mean the Mac is online or any model call succeeded.
4. The old ChatGPT-hosted private Site is a different origin, and this workflow does not publish to it. Use the verified Cloudflare HUD origin.

## One Mac setup step (required for OmniRoute, not Cloudflare AI)

The Mac must have the latest merged repo checkout, Node.js, Python 3, running OmniRoute, and both *existing* macOS Keychain credentials:

- `rovordigital.omniroute.endpoint`: local OmniRoute endpoint key.
- `rovordigital.hud.writer`: the same writer credential configured in Cloudflare/GitHub secrets.

From that checkout, run:

```bash
git pull --ff-only
bash tools/install_hud_chat_relay.sh https://rovor-hud-telemetry.rovordigital.workers.dev
```

The installer creates an isolated `com.rovor.hud-chat-relay` LaunchAgent and changes no existing OmniRoute or HUD telemetry LaunchAgent. It does not read or write model API keys outside their existing private OmniRoute runtime. It accepts the existing `rovordigital.hud.cloudflare.writer` Mac Keychain entry used by the working telemetry publisher (or the legacy `rovordigital.hud.writer` service); do not create, copy or paste another writer token.

**Cloud Groq, Mac-independent (PR #290):** Ask ROVOR's default **Cloud AI · no Mac** source can call the fixed `groq/openai/gpt-oss-20b` route directly from the existing authenticated Cloudflare HUD Worker to Groq's official HTTPS API. It does not use the local OmniRoute gateway, outbound Mac relay, telemetry publisher, or a second HUD. Local OmniRoute remains an optional, explicitly labeled source.

This cloud route is **disabled by default**. In the existing private GitHub environment `rovor-hud-production`, the owner must securely set `ROVOR_HUD_GROQ_API_KEY` as a secret (never in source or chat). After checking the **actual Groq free plan, commercial terms, organization/project quota and fallback behavior**, set the environment variables `ROVOR_HUD_GROQ_CHAT_ENABLED=true`, `ROVOR_HUD_GROQ_FREE_TIER_VERIFIED=true`, `ROVOR_HUD_GROQ_EVIDENCE_SHA256` (SHA-256 of privately retained eligibility evidence), `ROVOR_HUD_GROQ_VERIFIED_AT` and `ROVOR_HUD_GROQ_VALID_UNTIL` (epoch milliseconds, at most 24 hours apart), and a conservative `ROVOR_HUD_GROQ_DAILY_BUDGET` (1–30, no more than actual remaining account allowance). Re-run the existing **GitHub-owned PRIVATE ROVOR HUD (Cloudflare Worker)** deployment on main. Missing or expired proof disables the Groq model and inference. The digest/flags alone are *operator attestations*, not independent billing verification; renew only with real account evidence.

The Cloudflare Worker sends bounded requests to only `https://api.groq.com/openai/v1/chat/completions` with the exact Groq upstream `openai/gpt-oss-20b`. No flexible URL, paid fallback, multi-model fanout, tool execution, job replay or Mac endpoint is used. An atomic D1 local request counter, three-second spacing, daily allowance, fixed output cap, and short timeout fail closed. Other Groq organization/project traffic is **not measured**, so this local budget is not a provider quota guarantee. The new `/api/chat/groq/status` reader endpoint returns only cloud readiness, local request count, last completed model/token evidence and Mac-independent status; no key, prompts or output.

Cloudflare's existing `/api/hud/omniroute` metrics still describe Mac-origin OmniRoute snapshots; they can be stale while cloud Groq chat works. Do not equate a successful cloud Groq reply with current local OmniRoute telemetry.


Verify it is loaded:

```bash
launchctl print gui/$(id -u)/com.rovor.hud-chat-relay
tail -n 30 ~/Library/Logs/rovor-hud-chat-error.log
```

Sign in to the **Cloudflare** HUD, open Ask ROVOR and confirm a nonempty OmniRoute free-route catalog. Send one *non-sensitive* prompt and confirm the request transitions through queued → claimed → complete, with an actual answer. If the Mac is off, model requests do not execute. This bridge deliberately does not make provider inference permanently cloud-hosted.

## Free-only admission

The Mac enumerates the installed OmniRoute catalog but offers only explicit `:free` model routes and exact model IDs or combo IDs separately verified free and provided via optional `ROVOR_HUD_CHAT_FREE_MODELS` (comma-separated IDs). This explicit configuration is **not** automatically filled from an API key; the owner must verify each provider's free allowance, billing behavior and fallback rules before allowing direct model IDs that do not identify a zero-cost model. A free-named combo also requires verification of its underlying routes before using it. No round robin is introduced.

Enabling every one of the nine providers depends on current account access and a verified compatible model; a configured key is not proof of a usable, zero-cost model. The UI must say offline/unknown rather than invent activity.

## Task-aware routing and two-model review

Ask ROVOR's **Smart route** selects from the Mac's *currently advertised and explicitly free-eligible* model IDs. Its initial route-name and provider cues (coding, reasoning, speed, creative work) are **heuristic preferences, not proof that one model is objectively better**. The available route catalog, free-only policy and explicit provider constraints take precedence; there is no round-robin rotation or bypass of a disabled provider.

The **Two-model review when useful** option is off unless the owner deliberately enables it in the composer. When selected alongside Smart route, a comparison, provider-pair request or sufficiently complex task can choose **at most two distinct available routes**. The plan is visible **before Send**. A manually selected model remains a single-model call.

- Each model gets its own bounded, authenticated request and durable receipt.
- For the current **single-executor Mac relay**, calls are serialized so the second does not silently expire while waiting behind the first. If the first completes, the second model receives a limited copy of the first answer and performs an independent critical review. If the first fails, the second may independently attempt the original task. No paid fallbacks or repeated inference retries are enabled.
- Completion means a real response was returned. Responses are shown separately, with the requested route and receipt, **not** as an invented unanimous answer or verified ultimate fallback-model identity.
- Cancelling before claim is possible. Once a model has claimed work, stopping the browser wait cannot guarantee termination. No model has GitHub write access or autonomous job scheduling through this interface.

**Current evidence and remaining capability work:** Ask ROVOR now records *only* completed or Mac-reported failed chat receipts on the device that submitted them, retains counts for seven days, and uses a modest reliability tiebreaker after at least three recent receipts. Model-picker labels distinguish name-only coding/reasoning/speed hints from those actual completion records. End-to-end time includes the D1 queue; it is **not** provider inference latency, model quality, human PASS/FAIL, account quota or a cross-device global benchmark. No raw prompts, replies or credentials are written into these route statistics. Next add owner-reviewed quality outcomes by task family, verified task/tool compatibility and fresh per-provider quota/reset evidence before ranking models more aggressively. Never infer quota from request share, invent quality percentages, or imply the actual upstream identity of an OmniRoute combo is independently attested.

## GitHub source access — current scope

The Ask ROVOR composer now includes **GitHub source**, an optional, explicit selector of a curated set of eight files used for HUD, routing, deployment, and diagnostics. The Mac relay reads only the **local Git checkout's `origin/main` commit object**, using `git rev-parse` and `git show`. It sends a bounded source excerpt and the exact commit SHA to the selected OmniRoute model for analysis.

- A selected source excerpt **is transmitted to the selected model provider**. Do not select code containing credentials or customer data. The fixed allowlist excludes private receipts, local secrets and arbitrary paths.
- No GitHub access token is supplied to any model. The model does **not** get direct GitHub API tools, push/merge permissions, a shell or an unattended job scheduler in this chat upgrade.
- A local Git snapshot is not proof of the latest GitHub `main`. If you need updated context, fetch/review the repository safely on the Mac first (`git fetch origin main`); the model receives a commit identity, not a claim of a live repository read.
- If the source ref is missing or fails to read, the request fails as `repo_context_unavailable` **before** inference. It does not silently answer while pretending to have inspected GitHub.

For **actual GitHub code-editing employees**, the next independent capability is an owner-approved tool runner with narrowly scoped installation credentials that can read specific repository files, prepare changes only on feature branches, run tests, create PRs, and publish immutable receipts. It must not expose tokens in prompts, self-merge, push to `main`, or bypass owner PASS/FAIL. This is **not** implemented by granting the chatbot broader language-model instructions.

## Continuous OmniRoute chat reliability

The Mac relay republishes its model list and private heartbeat while processing a slow response. If the local OmniRoute gateway returns an explicit `401` or `403` **to its read-only model catalog request**, the relay can refresh the CLI session credential from the installed OmniRoute package and retry that catalog GET once. It never automatically retries an inference POST, a GitHub write, or a side-effectful operation. The Mac, network and gateway must still be running and free-only routes must remain verified.

## Recover 24/7 OmniRoute telemetry when the HUD shows an old report

The HUD can stay hosted online while its Mac reporter is offline. **A cloud-accessible HUD does not mean the Mac is sending live model usage.** The reporter is separate from the Ask ROVOR prompt bridge.

On the Mac, from the merged checkout:

```bash
bash tools/manage_hud_telemetry_agent.sh status
```

If not installed and the existing HUD writer key is in macOS Keychain, install the **separate read-only** reporting LaunchAgent:

```bash
bash tools/manage_hud_telemetry_agent.sh install
```

If it is already installed but not reporting, inspect `~/Library/Logs/rovor-hud-reporting-error.log` without sharing any secrets, then explicitly restart it:

```bash
bash tools/manage_hud_telemetry_agent.sh restart
```

The manager **refuses to overwrite an existing plist**, never starts inference, and does not change employee queues or STOP. Verify the private HUD advances its Mac last-report timestamp on two consecutive cycles. If it remains stale, check Mac network, OmniRoute local gateway authentication and the configured Cloudflare origin. GitHub's web deployment workflow cannot fix an offline Mac's LaunchAgent.

## Privacy and retention

Browser conversations are stored in that device's local browser storage; they are not synced between devices. Queued prompts and completed model replies are temporarily stored in the **private Cloudflare D1** database and cleaned by the Worker expiry mechanism (including a five-minute cleanup schedule). D1 backups may retain copies longer. Do not submit private client content to a free-tier model without explicit client authorization.

Reader and writer bearer credentials are distinct; only the reader can submit and poll, and only the existing Mac writer credential can announce/claim/finish. Neither key is stored in client JavaScript or committed to GitHub. The Mac does not expose OmniRoute on an inbound public port.

## Honest status and mobile verification

The Mac publishes a heartbeat while slow models execute, and the relay caps one inference at 100 seconds. A claimed request is not a completed request. Completed/failure receipts are retained locally in the conversation, but failed replies are excluded from future model context. The phone's Cancel control only cancels **queued** jobs; a request already claimed by the Mac may still complete. The requested route does not independently prove the fallback model that ultimately answered.

The iOS interface uses 16px form inputs to prevent Safari focus zoom, adapts to the visual viewport as the on-screen keyboard appears, and provides a dismissible conversation drawer. The same private HUD is accessible from iPhone, iPad, Mac and Windows browsers. Automated code checks are not a substitute for testing actual iOS Safari hardware and keyboard/orientation behavior.

## Later: Provider Manager

A future provider-key form should send keys to an authenticated backend with encryption at rest, redacted logs, scoped permissions, rotation and revocation; the keys must never be in localStorage, public Pages or GitHub code. Provider-specific connectors would discover models, determine free/billing eligibility, track usage where APIs support it and refuse unsupported quotas. That is **not included in this PR**.

## Groq live account usage monitoring (cloud-only)

The authenticated Cloudflare HUD now exposes a read-only Groq model catalogue
probe when opening Groq in Ask ROVOR or Workload Distribution. It uses the
**already configured** `GROQ_HUD_API_KEY` secret in the existing Worker to call
the pinned HTTPS `GET https://api.groq.com/openai/v1/models`. It is not inference,
does not submit prompts, does not use the Mac, and is D1-throttled across devices
to one catalogue probe per 60 seconds. GET
`/api/chat/groq/status?refresh=1` displays its result; normal status GET does
not perform an upstream call.

Only validated response-header values are cached in the **existing** private
D1 (`hud_groq_quota_probe`): `x-ratelimit-limit-requests` and
`x-ratelimit-remaining-requests` refer to *requests per day*, while token
headers refer to *tokens per minute*. Reset durations are taken from Groq
headers, not guessed. If the catalogue lacks headers or evidence is over two
minutes old, the corresponding quota is UNKNOWN. Catalogue presence and
rate-limit headers are **not a billing plan verification**, and cannot override
`groqCloudReady`, enable a paid route, or renew an expired zero-cost approval.
The receipt trail for actual inference remains separate and requires the
existing protected authorization and owner-approved quota gates.

## Automatic deployment proof of the Groq cloud key

After reviewed changes merge, the private GitHub Actions deployment now performs
a read-only (non-inference) Cloudflare → Groq `/models` check whenever
`GROQ_HUD_API_KEY` is present. The authenticated release readback reports
`cloud_groq_key_catalog`: whether that exact cloud key can list
`openai/gpt-oss-20b`, provider-supplied RPD/TPM headers if present, or a
truthful error state such as `auth_rejected`. It logs no key, prompts or
responses. This is distinct from the separate owner-approved free-only
inference gate, which still fails closed until verified; a catalogue readback
never claims an actual completion.

## Cloudflare-compatible redirect protection (Groq and Gemini)

Cloudflare Workers intentionally rejects `redirect: "error"` when creating
outbound `fetch` requests. Cloud-only Groq catalogue, Groq chat, Gemini chat
and Gemini Monitoring requests now use **`redirect: "manual"`** and explicitly
reject 3xx or other non-success statuses. They **never automatically follow**
redirects that could forward provider credentials. Node-based GitHub runner
read-only verification remains independent of the Cloudflare-specific behavior.
This corrects a runtime incompatibility without lowering free-tier admission,
changing any model, invoking an inference probe, or depending on the Mac.

## Why the Groq allowance meter can show UNKNOWN

Verified private Cloudflare readback returned Groq `catalog_received` and
`model_in_catalog:true`, but both `requests_per_day` and
`tokens_per_minute` were `null` on that response. The key and GPT-OSS
20B catalogue connection are good; **remaining allowance was not returned**.
Do not display an invented percentage, zero, or an offline Mac status. Groq
documents organization/project limits and API rate headers, but the model
catalogue check does not certify billing or infer a per-model spend balance.
Daily local admitted requests and actual completed chat receipts are
separate measurements from the private D1.

An expired 24-hour Groq Free-tier owner approval still prevents **every new
Groq inference call**. That expiry can no longer veto an otherwise authorized
production HUD/Gemini security deployment. The Mac is never required for
direct Groq/Gemini cloud chat, and an API key need not be re-entered.

## Cloud-only Ask ROVOR idea inbox (separate from inference)

The existing authenticated Cloudflare HUD now offers **Queue idea** in the
Ask ROVOR composer. It records up to 1,600 characters as a private D1
`pending_review` entry and returns an immutable receipt ID. The
**Cloud idea inbox** disclosure reads the most recent 20 pending drafts;
no Mac, OmniRoute, model key or Free-plan approval is required to submit.

Security boundaries are deliberate:
- The normal HUD reader login may submit **suggestions**, not approve, execute,
  alter project coordination, promote into `ghost_cloud_jobs`, merge PRs or
  change the GitHub repository.
- A same-origin POST is required; unknown request fields, oversized inputs,
  credential-like text and unauthorized requests are rejected. An atomic D1
  reservation allows up to 30 submissions per UTC day and spaces submissions
  at least five seconds across every Worker isolate; no unbounded spam loop.
- `queued:true` in an idea receipt means **draft saved**, not model request
  queued. `model_call_started:false`, `owner_review_required:true`.
  Keep idea text private; do not submit credentials, client materials or
  anything unsuitable for review by other authenticated HUD readers.
- Nothing in this lane grants a model repository credentials or execution
  privileges. Promotion to the existing canonical GitHub task queue, immutable
  approved task feed and reviewed cloud shift remains a distinct owner action.
  GitHub changes require a reviewed, least-privileged integration that creates
  bounded branches/PRs; models cannot push directly to main, release secrets,
  approve their own outputs, or bypass STOP/PASS-FAIL.

This is **phase one of cloud job intake**, not a claim that unattended GitHub
coding agents or 24/7 inference are already active. Existing hourly approved
cloud shifts are separately observed via the owner-private cloud workforce
status/receipts. The Mac is only an optional future compute booster.
