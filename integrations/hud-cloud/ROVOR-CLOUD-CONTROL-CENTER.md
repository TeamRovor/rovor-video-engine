# ROVOR Cloud Control Center — one GitHub workflow

**Goal:** One manual owner-run GitHub Actions workflow covering the existing Cloudflare
HUD, direct Google Gemini chat, separate nine-provider private Site cloud workforce,
provider eligibility, STOP, scheduled shift evidence, human PASS/FAIL review queue,
and source/coordination tests. **The Mac is never a required runner.**

[Run ROVOR Cloud Control Center](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/rovor-cloud-control-center.yml)

## How to use

Use the **Run workflow** menu on **main**.

| Input | What it does | Provider calls? |
|---|---|---|
| `audit_only` (default) | Offline code/security/queue tests + redacted live status from both existing clouds, saved in the GitHub job summary and seven-day artifact | None |
| `deploy_existing_hud` | Same audit, then *only when existing deployment secrets are valid* apply idempotent schema, publish the exact existing Cloudflare HUD, restore existing private reader/writer tokens and verify authenticated assets | None |
| `deploy_and_test_gemini` | Same plus an explicitly confirmed Free-tier Google project API key and **one** bounded Gemini Flash Lite response with an advancing private D1 receipt | One brief model request |
| `trigger_one_approved_shift` (default off) | Separately opt in to exactly one authenticated request to the existing private Site scheduler; only if owner STOP is enabled and at least one cloud provider is **currently eligible**. Real admission, quotas, approved canonical packets, receipts and deduplication remain the Site's responsibility | Only if private Site approves an existing job |

The workflow never runs Mac commands, copies local Keychain values, creates a second
Site, promotes a configured key into verified eligibility, edits immutable task
approvals, approves drafts, opens the STOP switch or retries attempted jobs.

**Credential prerequisites are evaluated before any production write.** Audits
produce helpful reports even when credentials are missing. A requested deployment
without the required secrets fails **at the readiness gate**, with specific
missing secret *names*, rather than starting a partial Cloudflare release.

## Existing production configuration (never paste values into source or chat)

Use the repository's existing `rovor-hud-production` Actions environment
and exact `ROVOR_HUD_DEPLOY_ORIGIN` variable pointing to
`https://rovor-hud-telemetry.rovordigital.workers.dev`.

Required for a Cloudflare HUD deploy: `CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID`, `ROVOR_HUD_D1_ID`,
`ROVOR_HUD_READER_TOKEN` and `ROVOR_HUD_WRITER_TOKEN`.
These must refer to the existing Worker and D1, not new ones.

Additionally, `deploy_and_test_gemini` requires `ROVOR_GEMINI_API_KEY`
(or existing `GEMINI_API_KEY`) from the owner-verified Free-tier Google
project. Confirm `confirm_free_tier` explicitly; merely finding
a Google API key does not prove zero cost, remaining daily quota, or permission
to send sensitive client material through Free tier.

For the independent private Site workforce **readback**, configure a
matching `ROVOR_GHOST_SERVICE_TOKEN` in the GitHub environment/repository
and the existing Site's `GHOST_SERVICE_TOKEN` (dedicated, 32+ printable
characters, distinct from all reader/writer tokens). The Site's native
service operation `status` is used to observe cloud admissions and review
counts. No GitHub action can retrieve an existing protected Site secret.

## Exact verification boundaries

The auditor reads only:
- Cloudflare HUD: private auth, direct Gemini listing/usage counters,
  Cloudflare AI listing, and optional Mac-origin telemetry.
- Private Site: nine provider admission/online states, STOP, scheduler
  receipts, queue and available review counts through a pinned authenticated
  **read-only** service operation.
- GitHub repository: local offline Node/Python tests of security,
  provider eligibility, immutable cloud job semantics, task routing,
  and source syntax.

A stale Mac telemetry timestamp is **informational**, not a reason the cloud
chat or private Site workforce should stop. The cloud Site may report nine
configured providers while *none* are eligible; the workflow leaves those
providers disabled rather than inventing quotas or unapproved jobs. An
`idle` scheduled shift means a wakeup occurred, not that AI inference ran.

The GitHub Steps **Summary** shows the redacted result. Downloadable
`rovor-cloud-readiness` and `rovor-cloud-final-readback` artifacts contain
only the same sanitized statuses/counts. No keys, prompts, client files,
private receipts or job IDs are put in the repository or artifacts.

## Scope limits, deliberately

- **No automatic provider billing verification:** every provider's actual
  free-tier eligibility and quota must be verified privately before Site
  admission; one Gemini cloud test does not activate all nine providers.
- **No auto PASS/FAIL:** the owner must review actual output in the existing
  authorized private Site/HUD. GitHub can report counts, not accept drafts.
- **No new scheduling service:** the existing private Site Site-linked
  `runScheduledShift` and existing GitHub hosted-shift schedule retain
  their distinct roles and safety gates. GitHub scheduled events are best-effort.
- **No unapproved production media work:** GUI tools such as Moho/Blender on
  local systems remain optional capability adapters; the cloud workforce
  doesn't pretend to control them.
- **No fake "all systems green":** a passed audit means tests and readback
  ran; a successful real inference requires a corresponding model receipt.

The old Gemini-only workflow remains as a narrow legacy operation; use
this unified workflow going forward. Do not rerun the obsolete queued
self-hosted Mac execution commit.
