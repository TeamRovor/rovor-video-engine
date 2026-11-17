# ROVOR cloud workflow execution map (source audit, 2026-11-17)

This is a **source-based map**, not proof that the deployed private Site, D1,
cron, credentials or individual providers are healthy. Regenerate the entire
machine-readable inventory with:

```sh
python3 tools/workflow_inventory.py --output workflow-inventory.json
python3 -m unittest discover -s tests -p test_workflow_inventory.py -v
```

The existing **Shared project loop checks** GitHub Action runs the audit on
changes to any workflow and publishes the `rovor-workflow-inventory` JSON
artifact. Flags are **review prompts**, not automatic permission or scheduler
changes. In particular, two matching cron expressions do not prove duplicate
provider dispatch.

## Present execution graph

```text
                           Owner-approved source / protected main
                                        |
                 +----------------------+--------------------+
                 |                      |                    |
             GitHub CI          GitHub read-only         Private Cloudflare
          project-loop-check     discovery / QA          Worker + D1 (runtime)
                 |                      |                    |
        workflow inventory     candidate / failure          STOP gate
        permission review        evidence only               |
                 |                      |                durable claim /
          isolated PR tests     Walter review / PR      free-only admission
                                        |                    |
                               owner-authorized changes   bounded job
                                                             |
                                                    D1 immutable receipt
                                                             |
                                                    private HUD readback
```

**Never interpret the GitHub Actions CI/discovery clocks as the production
provider-inference clock.** The repository identifies a native Cloudflare Worker
five-minute cron as the production shift owner, but the authenticated deployed
Site/Worker clock, source SHA and durable D1 claims still require private readback.
The older Site HTTP scheduler is not an alternative fallback.

## Keep / reconcile / disable decision table

| Existing lane | Observed source trigger / role | Decision | Evidence needed before changes |
| --- | --- | --- | --- |
| `integrations/hud-cloud/worker.mjs` + existing Wrangler config | Native cloud scheduled workforce (claimed authoritative) | **KEEP**; verify single runtime authority | Deployed SHA, cron registration, STOP, atomic D1 lease and fresh actual shift receipt |
| `ghost-cloud-github-scheduler.yml` | Confirmed `workflow_dispatch` legacy Site diagnostic; no cron | **KEEP manual-only**; do not restore cron | Ensure manual endpoint cannot compete or bypass protected environment |
| `rovor-autonomous-discovery.yml` | Hourly GitHub discovery and failure-triggered read-only triage | **KEEP separate** from inference | Prove it creates only reviewable candidates, no provider spending or repo mutation |
| `rovor-ai-workflow-factory.yml` | Every two hours; reads owner-approved proposals, may create PRs | **RECONCILE later** with reviewed GitHub engineering lane | Owner approval source, write token scope, no auto-merge, idempotent PR dedupe |
| `hank-cloud-watchdog.yml` | GitHub QA/watchdog | **KEEP as diagnostics** | Verify scheduled work never assumes successful production execution |
| `cloud-gemini-workforce.yml` | Manual owner control for a single approved task / STOP | **KEEP** explicit owner path | One-job bound, approved revision, true STOP readback |
| `rovor-cloud-control-center.yml` | Audit/readback only; intentionally does not deploy | **KEEP diagnostics** | No secondary deploy authority |
| `deploy-private-hud-cloudflare.yml` | Protected main/manual Worker deploy | **KEEP as sole deploy lane** | Tests, protected environment, authenticated live readback |
| `rovor-cloud-control-center.yml` versus `deploy-private-hud-cloudflare.yml` | Overlapping topic names, different privileges | **DO NOT MERGE** based on names alone | Confirm separate read-only versus deploy roles |
| All remaining Actions workflows | Generated machine-readable inventory | **REVIEW** before merging or disabling | Actual triggers, concurrency, permissions, dependencies and owner |

## Safe implementation sequence

1. Keep this audit in an isolated PR; inspect its full JSON artifact and hosted
   tests before changing any production workflows.
2. Reconcile existing #314/#316 HUD branches and #254/#444/#312 provider branches
   with main; do not merge clashing work blindly. #318 is a related diagnostics PR.
3. Use #412 for private D1/provider admission and fresh exact-model zero-cost
   evidence. A key or catalog listing alone does **not** prove live inference,
   remaining quota, or free-tier eligibility. Unknown is unknown.
4. Add no new GitHub cron dispatcher. Keep STOP before each dispatch, unique
   UTC-window idempotency, bounded lease and retries, max nine jobs per shift,
   and durable blocked/idle/success/failure receipts in the existing private D1.
5. Use #449/#450 for one bounded approved repo-read → branch → tests → **draft
   PR** engineering task, with Walter's backend review and owner-controlled
   merge/deploy. The Mac must remain optional.
6. Validate current private HUD against D1 and an actual pinned zero-cost
   provider receipt before claiming any provider is online.

## Audit limits

The parser uses only the Python standard library and reads YAML as *source
lines*. It is not a full YAML interpreter, does not expand expressions,
inspect secret values, or call the GitHub/Cloudflare APIs. Flags such as
`action_refs_not_sha_pinned`, `scheduled_without_explicit_concurrency` and
`default_token_permissions_unverified` identify reviews to perform;
they are not assertions of a vulnerability. Production permission changes,
cron removal, merges and deployments are deliberately excluded from this PR.
