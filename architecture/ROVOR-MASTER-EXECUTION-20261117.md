# ROVOR DIGITAL — Master Execution Directive
**Recovered from the November 17, 2026 engineering and workflow-efficiency sessions.**
**Status:** implementation charter, not deployment proof. Use the live default branch and private runtime evidence for all operational claims.

## End state
Build one continuously improving, multi-capability ROVOR intelligence system, not separate disconnected chatbot, video, GitHub, and dashboard projects. Walter coordinates a bounded task pipeline; specialist workers carry out narrow tasks using supported tools and verified zero-cost provider models; Hank independently evaluates results. GitHub is the shared source-and-review layer. The existing Cloudflare Worker/D1 provides cloud-first execution, durable claims, STOP, admission and receipts. The private HUD shows evidence, not projected activity. The Mac remains an optional specialized executor and must never be a prerequisite for cloud operations.

## Hard constraints
- **$0 model routing only.** A configured key, catalog entry, `:free` label or advertised quota cannot authorize a model request. Require exact pinned model identity, independently verified eligibility/terms, current quota where required, bounded canary authorization and STOP/permit checks. Never silently substitute paid or unverified routes.
- Preserve the **one production cloud-shift scheduler**, currently defined by the existing native Cloudflare Worker scheduled() binding. GitHub Actions must not gain a competing inference clock; auxiliary cron may check, report or propose only when reviewed.
- Preserve existing D1 state, canonical queue/claims, replay prevention, idempotent dispatch, usage receipts and global STOP. No duplicate D1 or replacement HUD/Site.
- **Repository is public.** Never commit credentials, private receipts, provider/account IDs, customer data, prompt contents, tokens, private URL credentials, or production secrets.
- Walter may perform automated review; removing PASS/FAIL from the HUD's presentation must not remove protected owner authorization for merge, deploy, credential/billing changes or STOP modifications.
- Branch-scoped GitHub App permissions, non-secret task context, tests and reviewable PRs. No model-automerge, direct protected-main writes or automatic production deployment.
- No false "9/9 online", invented usage percentages, synthetic employees, or test-success-as-delivery claims.

## Single execution graph
1. **Intake:** read `coordination/tasks.json` (sole ownership/dependency record), paired `coordination/work-routing.json`, repository state, worker capabilities and explicit owner-approved work scope.
2. **Walter supervisor:** classify goal and constraints, choose a small measurable task, avoid conflicting claims, create a bounded versioned work packet.
3. **Admission:** verify STOP, owner permissions, fixed provider/model ID, fresh free-only eligibility, quota/reservation, token budget, replay window and privacy policy. Keep credential configured / catalog found / eligible / canary passed / quota known distinct.
4. **Cloud dispatch:** existing Worker scheduling and D1 claim lease only. Select best eligible provider according to task capability, observed quality/latency and available capacity (not round-robin). Fail closed on 429, timeout, expired eligibility and missing evidence.
5. **Engineering execution:** read a pinned repo revision; propose isolated diffs only on branches; run scoped tests; produce a draft PR with exact base/head/changed paths. Non-code work uses the same task/acceptance/receipt contract.
6. **Hank verification and Walter review:** independently test against immutable artifact hash and task acceptance; record PASS/FAIL as backend evidence, but never interpret automated review as merge/deploy authorization.
7. **D1 receipts → HUD:** show task state, real timestamps, exact provider/model, measured tokens when exposed, admission failures, quota **unknown** when unverified, queue state and STOP. Show infrastructure/transport errors explicitly.
8. **Continuity:** on every shift record an immutable bounded receipt (idle / blocked / success / failure), owner/claim, task revision, next action and verified artifacts. Prevent duplicate or failed-job replay.

## GitHub Actions ownership lanes (logical targets, not an instruction to delete jobs)
| Lane | Responsibility |
| --- | --- |
| CI | Path-scoped tests and code-quality checks |
| Security | Scheduler, STOP, credential/exposure, branch and policy guards |
| Deploy | One protected deployment owner with verified rollback |
| Workforce dispatch | Manual/approved entrypoints; production shift clock stays in Cloudflare |
| Workforce verify | Receipts, model-policy tests, workload regressions |
| Maintenance | Read-only inventory, reports, proposals and hygiene |

Prefer **one owner per responsibility** and reusable components before a bulk workflow collapse. Preserve current workflow IDs required by branch rules and any external caller until an equivalent verified replacement is in place. The source inventory counted 74 workflow files in the November 17 snapshot; the count is not a performance target.

## Sequenced work and evidence gates
**P0: prevent scheduler drift.** Harden the existing schedule guard, preserve the production Cloudflare binding, capture passing tests and an inventory before retiring redundant checks. Reconcile active governance PR #454 and merged #457; do not duplicate their work.

**P1: provider truth and admission.** Complete #412 with authenticated private Site/D1 readback, correct deployed SHA and exact-model free eligibility. Reconcile overlapping catalog fixes #254/#444. Nine provider rows are required, but each must show a factual stage; stale, unknown or disconnected is not online.

**P2: one real engineering job.** Through the existing cloud runtime, execute an explicitly approved bounded task (repo read → implementation branch → tests → draft PR). Persist upstream model response/token receipt and worker task outcome, never secrets. STOP, 429, no-replay and idempotency tests must pass. Match #449/#450 before adding overlapping orchestration.

**P3: HUD connected to evidence.** Reconcile #314 with stacked preview fix #316 and the read-only private receipt bridge #456. Fix branch conflicts, run mobile/desktop and security checks, validate authenticated D1 readback and only then authorize protected deployment. No Mac pairing requirement.

**P4: Ask ROVOR model intelligence.** Advance #309 with strict structured intent, capability/quality-aware route scoring, a protected policy gate, bounded specialist calls, verified model receipts and accessible phone UX.

**P5: measurable autonomous improvement.** Once verified P0–P4, expand task capabilities and backlog safely, keep owner review for irreversible actions, and score useful deliverables (not run counts). Maintain repo/task memory, concise incident recovery, and one authoritative engineering change queue.

## Proof that the system works
- One current, **real** zero-cost, pinned-model canary receipt with time, exact upstream ID, outcome, and tokens where supplied.
- One approved cloud-only task generating a tested draft engineering PR with immutable source/CI/receipt pointers and separate Walter/Hank review.
- Fresh private D1-backed HUD readback matching the receipt; all nine provider rows truthful and quota unknown where unproven.
- One STOP-denied dispatch, one replay-denied attempt and one 429/no-paid-fallback test.
- Cloud execution with no Mac or local tunnel; one scheduler; no autonomous merge/deployment.

## Operating rule
Continue the highest-impact *unclaimed* safe task using current main and current PRs. Record one shared claim, make a focused reversible change, run relevant tests, capture exact evidence, publish a PR and hand off. If secrets or private Site access block proof, report the missing check precisely and continue independent safe repository work; do **not** simulate success.
