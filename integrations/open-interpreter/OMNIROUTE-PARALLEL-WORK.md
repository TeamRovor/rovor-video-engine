# ROVOR OmniRoute — parallel draft-workers for the always-on Mac project

**Stage:** Prepared and offline-testable, **NOT dispatched to the owner's Mac or executed by external models yet**. This workstream is independent of the iPhone chat's `mac-execution-roundtrip` task. Follow the canonical `coordination/tasks.json` ownership; do not claim the phone's runner workflow, Jane's PR #45 bootstrap files, original media or Final Cut.

## Reuse what's already installed

Earlier actual Mac Terminal evidence showed OmniRoute on `http://127.0.0.1:20128` and working provider connections for Cloudflare AI, Gemini, Groq Primary and Mistral. The inference endpoint key was stored as a macOS Keychain item with service `rovordigital.omniroute.endpoint`. The `rovai` Codex route was attempted but streaming stability remained unverified. Existing combo routes `rovor-fast-free-v1`, `rovor-code-free-v1`, `rovor-reason-free-v1`, `rovor-vision-free-v1` were configured but should **not** be presumed working, unlimited or no-cost. Note that `integrations/open-interpreter/OMNIROUTE.md` still contains earlier installation-stage observations; newer host evidence supersedes those older status lines. This ChatGPT session does not currently execute commands on that Mac; a GitHub commit does not activate local OmniRoute.

## Three jobs optimized for modest-cost external models

| Workpack | Best agent skill | Grounded output | Deliberate boundary |
| --- | --- | --- | --- |
| `runner-blocker` | Fast evidence triage | Diagnose why the existing GitHub self-hosted Mac workflow is queued; rank hypotheses and request decisive proof | Do not touch runner registration or repeat the existing proof job; phone session owns that lane |
| `supervisor-resilience` | Coding and architecture critique | Minimal LaunchAgent+SQLite+STOP/lease supervisor design and deterministic tests | No extra queue/database, automatic GUI imports, or assumption the Mac is unlocked |
| `provider-efficiency` | Model-routing and benchmark analysis | Conservative OmniRoute task/model rubric, measurable latency/cost/reliability scorecard | No presumed free credits, third-party secrets, paid fallback or switching Codex/Interpreter implicitly |

Each checked-in packet in `coordination/omniroute-workpacks/` includes specific public-source paths, deliverable and falsifiable acceptance criteria. The model output is **draft-only** and requires human/ChatGPT review. Outputs are not automatically committed, emailed, posted or executed.

## Safe executor

`tools/omniroute_workpack_runner.py` is one small Python standard-library client. It uses the **existing** local OmniRoute authenticated `/v1/chat/completions` gateway and allows at most **two simultaneous requests**. It does **not** use Open Interpreter as an operating system executor and cannot control native applications. No arbitrary tool/function call, filesystem scan, shell execution, social posting or external URL is allowed.

From a trusted local checkout of this branch, a **no-model preview** is:

```bash
python3 tools/omniroute_workpack_runner.py --all
```

Actual on-Mac model calls require deliberate authorization, a specific provider route and a review that OmniRoute has **no upstream paid fallback**. Example of the **interface only** (replace placeholders with actual confirmed eligible routes; never paste secrets):

```bash
python3 tools/omniroute_workpack_runner.py --all \
  --route 'runner-blocker=VERIFIED_FAST_ROUTE' \
  --route 'supervisor-resilience=VERIFIED_CODE_ROUTE' \
  --route 'provider-efficiency=VERIFIED_REASON_ROUTE' \
  --approve-model-use --confirm-no-paid-fallback
```

Do not run this until the actual routes and provider billing/quotas have been independently checked on the Mac. The `--confirm-no-paid-fallback` option records the operator's decision; **it does not inspect or enforce OmniRoute's upstream billing configuration**, so a provider itself may still charge. The client never chooses a model or paid fallback on its own. One explicit `--model VERIFIED_ROUTE` can also serve all selected packets after its suitability is checked.

The client reads only checked-in, bounded public ROVOR files, retrieves the local endpoint key from the environment or the existing macOS Keychain service (without writing or printing it), and uses `Authorization: Bearer` over loopback. It stores receipts in `~/Documents/Rovor/OmniRoute-Draft-Receipts` (private folder, 0700). For each packet, a reserved receipt is saved *before* inference; if interrupted or failed it is never silently rerun. It emits task-specific elapsed time, selected route, usage tokens **only if reported** by the provider, output draft and evidence input hashes. It cannot claim whether a route is free, a Mac app was controlled, a GitHub merge happened or a worker is actually persistent.

## How it accelerates without duplication

**iPhone ChatGPT**: continues the independently owned Mac runner/PR review work. **OmniRoute draft agents**: asynchronously prepare three bounded research/quality packets, then a reviewing ChatGPT can convert good findings into new non-overlapping canonical tasks. **Real Mac supervisor (future)**: runs safe approved packets and records receipts when the Mac is actually awake and the private task bridge is operational. No independent OmniRoute daemon, supervisor installation, or schedule is deployed by this change.

To prove *running*, require all three of the following: a real local model call (not a mocked hosted test), a non-sensitive receipt with job id/model/status and elapsed time, and an actual coordinator confirming it read the receipt. GitHub CI proves only the offline no-side-effects runner.

## Validation

`python3 -m unittest discover -s tests -p test_omniroute_workpack_runner.py -v` is fully offline. The GitHub `.github/workflows/omniroute-workpack-check.yml` matrix tests Python 3.9/3.11 and verifies the no-model dry run. No hosted CI test contacts provider endpoints.
