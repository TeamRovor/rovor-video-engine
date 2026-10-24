# ROVOR 24/7 ghost employees — hybrid cloud/Mac and provider roles

**Owner direction:** 2026-10-23. **Status: architecture and policy only.** This document does not establish Cloudflare deployment, active AI provider accounts, Mac remote execution, continuous reasoning, a Discord/Telegram sender or model billing eligibility. It supplements [ROVOR-AI-PLAN.md](../ROVOR-AI-PLAN.md), and does not replace the tested local LaunchAgent/SQLite worker, [WORK.md](../WORK.md), [AGENTS.md](../AGENTS.md), or the existing shared development task queue.

## Employee identities do NOT depend on model vendors

- **Walter — supervisor:** takes Amar's daily goal, drafts a bounded plan, breaks it into auditable steps, tracks dependencies, selects the correct named specialist, verifies each handoff and escalates blockers. **Gemini** is the preferred reasoning engine if configured and eligible.
- **Mike — Mac systems:** supervises authenticated terminal/control channel, STOP, launchd health and troubleshooting; read-only by default.
- **Jane — Final Cut / video editing:** researches native project workflows and safe FCPXML; no unsupervised real library import.
- **Jesse — Moho / 2D:** researches facial rigging, lip sync, visemes and animation staging; preserve source art.
- **Gale — Blender / 3D:** researches isolated scenes, render pipelines and reproducible output checks.
- **Gus — operations:** organizes client intake, schedules and internal delivery; no unauthorised client account edits.
- **Saul — marketing:** researches brand content and ethical outreach; no automated posting, DMs or sending without approval.
- **Hank — QA:** challenges plans, verifies source evidence, tests code/workflow outputs and rejects misleading claims.

Each employee has a **persistent role and own research sequence**, but its model provider can vary by subtask. Providers are tools used *by* employees, not replacements for Walter, Mike, Jane, Jesse, Gale, Gus, Saul or Hank. Existing role manifest: [ghost-role-bootstrap.json](../coordination/ghost-role-bootstrap.json).

## Inference provider hierarchy — dynamic, free-first, never implied free

| Route | Intended workload | Mandatory precondition |
| --- | --- | --- |
| Gemini via Google AI Studio | Walter's daily planning, hard reasoning, long repository/log context | Verified API key, eligible free model/quota, privacy review |
| Groq | Quick parses, small code snippets, syntax triage | Live account/model limits and zero-cost eligibility |
| NVIDIA NIM | Alternative fast inference and code diagnostics | Live API/model limits; **commercial usage/license terms** explicitly verified |
| Mistral | Precise code implementation, debugging, code review | Verify actual applicable free-tier availability; otherwise wait |
| OpenRouter | Emergency model fallback after providers fail | **Only** a current, explicitly verified free model and remaining quota; never silently route to paid options |
| Cloudflare Workers AI | Optional cloud-side inference | Separate model/allowance checks; **not the same service as Cloudflare Cron scheduling** |

The existing Mac OmniRoute proxy is a **local loopback service**; a Cloudflare Worker cannot call that Mac localhost address. Deploying a cloud planner requires approved direct HTTPS provider adapters, or a separately authenticated outbound Mac polling protocol. No provider is configured or charged by this policy. A fast provider is not automatically the best model for every job. Pin tested model IDs and version them after live verification rather than making unsupported claims about availability or speed.

**Default spending limit = $0.** Recheck plan/model tier, eligibility, quotas and provider/model terms before each dispatch. Record the **exact model actually used** and failure category. Prefer in-provider fallback only when still verified free, then another eligible free provider, then a checked OpenRouter free model. Unknown cost means **not eligible**. A generic OpenRouter model router and Anthropic Claude Haiku must never be assumed free. Third-party free-tier prompts may be used for service improvement; do not send keys, personal or client data, unpublished audio or original private artwork without authorization and provider-policy review.

## Hybrid control plane that stays available when the Mac is away

```text
Amar / Evan / approved task  ->  GitHub claims + ROVOR goal
                   |
              Walter (Gemini when eligible)
                   | bounded, versioned job proposals
                   v
    Future Cloudflare Cron scheduled() every ~5 minutes
                   |
         D1 durable role jobs / leases / receipts
                   |
         Model router / quota & cost eligibility
              | Groq / NVIDIA NIM / Mistral
              | Gemini / explicit free OpenRouter fallback
                   |
                   +--> review-only drafts / checkpoints / QA
                   |
                   +--> separate authenticated private Mac queue
                                   |
                        EXISTING Mac launchd + SQLite worker
                                   |
                    host-approved terminal/Moho/Blender/FCP
                                   |
                         private execution receipts
```

- **Cloud always available for coordination** (subject to Cloudflare service, plan limits and deployed configuration). D1 holds runtime job status, checkpoints, leases, provider attempt caps and Mac pending tasks. GitHub keeps source/versioned development claims; don't create another contradictory public task-owner queue.
- **Mac handles local apps** only when logged in, awake and online. Existing `com.rovor.ghost-worker.readonly` remains the single running local executor until intentionally migrated. Never add a duplicate Mac LaunchAgent, open a privileged self-hosted runner in the public GitHub repo or expose Mac localhost on the internet. The private bridge must be proven with a real `system.ping` and then one opt-in fixed command before any advanced actions.
- **No fake 24/7 inference guarantee:** cloud Cron can wake a lightweight scheduler 24/7, but agents pause at exhausted inference quotas or offline resources; they resume from durable checkpoints later. No busy-spin or infinite attempts.
- **No premature CrewAI/LangGraph/AutoGen migration:** use a small state machine and existing workers first. Evaluate a framework only if deployment evidence shows it solves a specific missing capability.

## Reliable job state, retry, approvals, reports

Every job has immutable ID/dedupe, named specialist, allowed operation, source/ref, provider+exact model, quota/cost check, status, checkpoint, attempt count, error class and review receipt. The state machine is **proposed -> approved -> queued -> running -> needs_review/completed/blocked**, with single-owner lease/reconciliation. A provider timeout after an uncertain external effect is **not** evidence that no action happened.

For a *provably idempotent, read-only model draft only*, up to **three** attempts are permitted if remaining quotas allow; respect `Retry-After`, use bounded backoff, and preserve the job/attempt ledger. After three failures pause and notify Amar via a separately **configured, tested, permissioned** Discord/Telegram channel or dashboard; absent notifier, persist `needs_review` visibly. Terminal commands, GUI changes, email/social sends, publishing, payments and other side effects **never automatically retry** after uncertainty. The current failed scheduled OmniRoute job is terminal and must not be replayed. Keep its existing five claims per rolling 24 hours until the Mac owner explicitly revises that policy.

## Rollout gates, in dependency order

1. **Preserve working Mac baseline:** do not replace the existing 5-minute local worker. Resolve the real scheduled OmniRoute HTTP 502 / empty-response issue with a **new** separately approved test job, not the failed ID.
2. **Prove the private Mac channel:** use the existing one-pass bootstrap and scoped Keychain credential. Confirm a signed-in actual Mac-origin private issue receipt, then the separately approved fixed terminal probe.
3. **Configure eligible inference providers separately:** verify connected Google/Groq/NVIDIA/Mistral/OpenRouter accounts, model IDs, free limits, license suitability and exact usage receipts without posting credentials; test one planner and one specialist draft, with Hank's checks.
4. **Stage a Cloudflare control plane only after account authorization:** one Cron Worker, minimal D1 schema, no public job payloads, keyed inbound/outbound auth with rotation, private state, STOP, dead-letter/review, cost governor, and idempotent handoff to existing Mac; dry run before live Cron. Do not deploy automatically from this public repository.
5. **Verify continuity:** task resumes after chat closes, quota exhaustion, cold Mac, lost Wi-Fi, crash and duplicate enqueue; record two or more independent scheduled wakeups and human-review delivery. Only then label a named employee "24/7 available". Native GUI success is a separate gate.

## Official docs checked October 2026

- Cloudflare scheduled handlers: https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/
- Workers Free plan limits: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare D1 and Free tier: https://developers.cloudflare.com/d1/platform/pricing/
- Cloudflare Workers AI *separate inference pricing*: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Gemini API quotas/free models: https://ai.google.dev/gemini-api/docs/rate-limits and https://ai.google.dev/gemini-api/docs/pricing
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Mistral usage allowances: https://docs.mistral.ai/admin/billing-usage/usage-limits
- NVIDIA NIM trial/developer usage: https://docs.api.nvidia.com/nim/docs/product
- OpenRouter free-model caps and routing: https://openrouter.ai/pricing and https://openrouter.ai/openrouter/free/apps
