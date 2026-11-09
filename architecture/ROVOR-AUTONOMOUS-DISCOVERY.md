# ROVOR autonomous cloud work discovery

The owner should **not** have to manually feed every new task into Ask ROVOR.
The existing private cloud idea inbox accepts reviewed proposals, while this
dedicated GitHub Actions job searches for useful evidence **every hour**, even
when the Mac, mobile app and browser are all closed.

## Real, bounded capabilities

- GitHub Actions (on trusted `main`) checks the existing private TeamRovor
  repository's **failed recent main workflows**, newly updated unassigned
  security/bug/reliability issues, and older unassigned PRs that need review.
- Proposals are ranked by evidence: main CI failures first, then security and
  regressions, then accessibility/HUD issues, then stale PR review. A run with
  no actionable evidence produces no fake work.
- The job reads the 20 most recent entries in the existing *private*
  Cloudflare D1 idea inbox and skips already recorded discovery signatures.
  It submits **at most one proposal per hourly run** and at most six recent
  automatically discovered proposals per UTC day; the HUD's own atomic
  daily limit and pacing additionally apply. It never logs private idea text.
- It reuses existing GitHub Action credentials for **read-only** repository,
  issues and CI status, and the existing protected
  `rovor-hud-production` HUD reader secret. No new user API key, Mac
  connection, GitHub App registration, paid model or external third-party
  service is required. Browser and client credentials are never leaked.
- All submissions use the existing `POST /api/hud/ideas` endpoint, which
  always returns `state: pending_review`, `model_call_started:false` and
  `owner_review_required:true`; these are **not scheduled AI coding jobs**.
  No model is called or given GitHub write access by discovery.

**Separately** the existing scheduled cloud workforce uses the canonical
approved-task feed, STOP and owner PASS/FAIL. This discovery lane does not
skip that authorization. Future approval policy can permit *preauthorized,
reversible, bounded* research/PR preparation without human prompting on
every draft, but only after a real verified-zero-cost provider, scoped
GitHub credentials and receipts are proven. Models must never approve their
own work, push to `main`, change billing, alter protected deployment settings
or grant wider permissions. A draft PR may be prepared unattended under
explicit scope, but merging/releasing still requires the existing review gate.

## Verifying it

PRs run `node --test tests/test_rovor_auto_discovery.mjs` without secrets.
After the workflow is merged into `main`, GitHub Actions schedules the
hourly run at minute 17, protected by the existing production environment.
A manually dispatched run remains an optional diagnostic/recovery route;
normal operation requires no manual input. GitHub scheduled Actions are
best-effort and can be delayed or skipped by GitHub; they are not a guaranteed
real-time uptime service. Logs return short states such as
`owner_review_draft_queued`, `no_new_evidence_backed_work`,
`daily_draft_budget_reached` and `credentials_unavailable`. Only the
actual private inbox receipt and CI logs establish that a proposal was saved.

This lane never uses the local OmniRoute relay. It can find work while the
Mac is off; local compute acceleration can be added later as an explicitly
optional capability.
