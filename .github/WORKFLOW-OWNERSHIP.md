# ROVOR GitHub Actions ownership and execution policy

## Single execution owner

- **Cloud shift timer:** the existing native Cloudflare Worker scheduled() binding and cron, protected by private D1 claims, quota reservation, verified zero-cost eligibility and STOP. Do not restore a GitHub cron posting to the old private Site endpoint.
- **GitHub Actions:** read-only checks, owner-initiated diagnostics, safe PR proposals and the separately protected deployment workflow. A GitHub Actions schedule for reporting or proposal publishing does not imply model inference.
- **Production deployment:** deploy-private-hud-cloudflare.yml remains the owner. Do not reintroduce deploy code in older control-center workflows or expose provider keys to pull-request runs.
- **Provider admission:** model-catalog discovery proves catalog availability only. Exact pinned model, fresh zero-cost commercial eligibility, provider-scoped quota and an approved canary are separate gates.
- **Review:** Walter automated review, human approval, GitHub CI and exact model receipts are separate evidence categories. Reviews cannot bypass STOP, quotas or deployment boundaries.

## Changes to routine CI

1. Use targeted paths filters, and include cloud runtime files in their policy tests.
2. Prefer PR checks and push branches main to prevent doubled feature-branch/PR runs.
3. Use per-PR concurrency and cancel-in-progress only for disposable offline tests; never for production dispatch, D1 writes, migrations or deployment.
4. Set short timeouts, minimum token permissions and checkout persist-credentials false in offline checks.
5. Add changes on a dedicated branch, run tests and open a reviewable PR. Avoid mass renames or deletions that break operator entry points.
6. Do not introduce a second cloud scheduler. The retired ghost-cloud-github-scheduler.yml remains manual-only.
7. An online model requires a timestamped provider/model/token receipt; stale OmniRoute data or a successful catalog check is not such proof.

## Read-only inventory audit

Run without provider secrets or network access:

    python -m unittest discover -s tests -p test_workflow_topology.py -v
    python tools/workflow_topology.py --check --format markdown
    python tools/workflow_topology.py --format json

The workflow-topology-audit.yml check inventories the workflow fleet, warns about topology debt and fails if the old GitHub-to-Site shift cron is reintroduced. It does not change any runtime or authorize inference.

## Separate follow-ups

- Reconcile model ID and catalog PRs #254 and #444 before merging either.
- Review cloud-first mobile HUD PR #314 separately from workflow changes and private Site publication.
- Verify nine-provider availability with fresh private cloud receipts, not saved credentials.
