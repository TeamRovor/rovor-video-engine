# Walter's 14 OmniRoute-compatible role packets

**Operational truth:** 14 additional review-only JSON packets are now generated into the pre-existing public workpack directory, with exactly the structural fields, visibility flags, role categories, input limits and task length restrictions of the OmniRoute workpack runner in active PR #41. This does not activate them. The legacy runner currently maintains a separate hard-coded allowed-packet list (five entries), while the active Mac-only scheduler has a separate single-entry work plan and route membership map. Consequently, these packets cannot execute until the owner of those overlapping files incorporates and reviews them.

## Executable source compatibility

- `coordination/walter-approved-research-backlog.json`: canonical reviewed Walter assignment list, two assignments each for Mike, Jane, Jesse, Gale, Gus, Saul and Hank
- `coordination/omniroute-workpacks/walter-v1-*.json`: 14 deterministic, fixed public-source `schema_version=1` packets
- `tools/walter_workpack_compile.py`: read-only compiler and drift/integrity check matching the current legacy packet parser's field rules; never writes or invokes a model
- `tests/test_walter_workpack_compile.py`: verifies role coverage, original allowlist noncollision, packet limits, tamper detection, symlinked file/parent denial and no automatic effect or dispatch approval
- `.github/workflows/walter-workpack-compile.yml`: hosted Python 3.9/3.11 compatibility suite; no secrets or Mac access

**Existing runner integration, deferred to the active Mac owner**: after resolving the two new HTTP 502/empty-choice failures, add reviewed packet slugs to `omniroute_workpack_runner.PACKETS` and `ghost_omniroute_job.ROUTES`; separately stage no more than the allowed existing five claims per rolling 24 hours through `ghost_omniroute_feed.PLAN`, using the immutable dedupe keys from the Walter manifest. The free-route catalog, billing eligibility, STOP, private receipt containment, and previous-failure no-replay rules must remain enforced. No model-selected jobs or automatic repeat loops may enqueue themselves; when finite work is exhausted, return needs-review rather than fabricate indefinite productivity.

These 14 packet files contain only explicitly approved public repo input paths and no private client data, audio, keys, local user paths or passwords. The generated `role` values `evidence-triage` and `software-architecture` are the current runner's **task category enum**; the packet's unique `id` and `task` identify the ROVOR specialist. Neither value grants app control or a model subscription.

## Verification boundary

- Hosted CI proves checked-in packets are structurally compatible with the reviewed PR41 runner **except for its unmodified explicit slug allowlist**. It does not verify any actual inference, free tier availability, macOS tools, background continuity or report quality.
- A live Mac success requires fresh approved jobs saved with distinct IDs, private review-ready receipts, and automatic following work without reopening ChatGPT.
- There must be no second local worker, public privileged GitHub runner, auto-activated terminal command, unauthorized free-tier fallback, or replay of previously failed job IDs.

This is a building block for the already active Mac OmniRoute workstream, not a second Mac worker claim.
