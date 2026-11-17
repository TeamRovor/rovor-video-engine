# GitHub Actions efficiency audit — 2026-11-17

This document records a source-level inspection, not production runtime proof. Run `python3 tools/workflow_inventory.py --output /tmp/rovor-workflows.json --fail-on-dispatch-cron` to generate the complete machine-readable inventory of the repository's YAML workflows and flag accidental scheduler additions to known dispatch lanes. The tool is offline, read-only, has no credentials, and does not claim to fully parse or validate YAML. The existing legacy scheduler's PR/push test lane runs this inventory and fails if an identified dispatcher is given a GitHub cron; the protected manual shift is unchanged.

## Observed default-branch baseline

- 72 workflow files on `main` at `dc851400b0f5` when rechecked on 2026-11-17 (later merges may change this count).
- `ghost-cloud-github-scheduler.yml`: **manual legacy Site diagnostic only**; production cron removed.
- `ghost-cloud-scheduled-shift.yml`: offline safety test only, not a scheduling authority.
- `rovor-cloud-control-center.yml`: diagnostic/readback only; deployment owned by `deploy-private-hud-cloudflare.yml`.
- `rovor-autonomous-discovery.yml`: GitHub cron `17 * * * *`, plus manual and failed-CI discovery; explicitly read-only discovery, not model dispatch.
- `rovor-ai-workflow-factory.yml`: GitHub cron `11 */2 * * *`; reads owner-approved D1 drafts and proposes PRs with write permissions limited to its publishing job.
- `hank-cloud-watchdog.yml`: GitHub cron `17,47 * * * *`; separate watchdog responsibility.
- The existing Cloudflare Worker native cron is documented as the production cloud workforce scheduler. Do not add a second GitHub production dispatcher.

## Ownership and keep/merge/disable decisions

| Lane | Current owners/entry points | Decision | Required verification before modification |
| --- | --- | --- | --- |
| Production cloud shift | Cloudflare Worker scheduled handler | **KEEP** one canonical authority | Live deployed source/version, scheduled events, D1 idempotency, STOP before dispatch |
| Legacy Site shift | `ghost-cloud-github-scheduler.yml` | **KEEP manual diagnostic only** | A verified replacement and owner authorization before eventual removal |
| Discovery | `rovor-autonomous-discovery.yml` | **KEEP** non-dispatching | No provider inference or unauthorized task claims |
| Reviewed proposal factory | `rovor-ai-workflow-factory.yml` | **KEEP, evaluate consolidation** | D1 review authorization, no unreviewed workflow execution, PR-only writes |
| Cloud readiness | `rovor-cloud-control-center.yml` | **KEEP audit-only** | Verify no deploy or duplicated shift calls |
| HUD deployment | `deploy-private-hud-cloudflare.yml` | **KEEP sole deployment owner** | Protected production environment and readback |
| Historical/Mac diagnostics | `moho-*.yml`, `rovor-mac-*.yml` | **KEEP isolated, inventory for archival later** | Prove no production cloud dependency on Mac |
| Other cron/event workflows | All remaining YAML workflows | **REVIEW** using inventory JSON | Actual triggers, job-level scopes, runtime evidence, callers, cost |

## Before → proposed execution graph

Before: Worker cron → D1 scheduling/STOP; independent GitHub discovery, factory, and watchdog schedules; manual legacy Site diagnostic. These paths must not be described as identical without call-level evidence.

Proposed: **one canonical cloud shift scheduler** → STOP/lease/idempotency check → exact free-only provider admission → bounded job → immutable redacted receipt → private HUD readback. GitHub discovery and reviewed PR preparation stay separate, rate-bounded *auxiliary lanes* unless further evidence shows real duplicate dispatch.

## Next implementation slices

1. Run full offline inventory and inspect all cron jobs for hidden dispatch and write scopes. Enforce the no-duplicate-dispatcher guard in CI.
2. Trace Cloudflare Worker schedule source, D1 task claims and evidence against deployed SHA; verify STOP and replay protections.
3. Review existing PRs #314/#316/#318 (HUD), #254/#444 (provider admission), #312 (registry), and issue #412 before changing overlapping files.
4. Run one approved bounded engineering change through branch → tests → draft PR → Walter review → redacted receipt, without auto-merge or auto-deploy.

## Non-negotiable

No paid model routes or fallback; nine configured credentials are **not** nine verified inference providers. Unknown quotas remain unknown. No Mac dependency. Never disable a production schedule on the basis of this source audit alone. Protect STOP, secrets, D1 receipt integrity and human release approval.

## Governance deduplication (follow-up)
The `.github/workflows/workflow-governance.yml` job now owns all source-policy
checks in one read-only, pull-request/push gated CI lane:
approved auxiliary crons, known dispatcher inventory, and the retired legacy
scheduler's main-only/manual/protected-environment requirements.

The redundant `legacy-scheduler-policy.yml` CI entrypoint is retired **only
after** its `tests/test_legacy_scheduler_policy.py` and
`tools/check_legacy_scheduler_policy.py` assertions are invoked by the
central workflow. The existing `ghost-cloud-github-scheduler.yml` retains
its original offline hosted-shift tests and protected, explicitly confirmed
manual diagnostic; only redundant inventory test steps and their extra
triggers are removed. No production cron, provider dispatch, Site secret,
approval, D1 table, or STOP gate is touched.
