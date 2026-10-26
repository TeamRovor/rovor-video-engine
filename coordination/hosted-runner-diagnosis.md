# ROVOR GitHub Actions — failed before any recorded execution step

**Checked:** October 21, 2026. **Scope:** GitHub-hosted CI availability and diagnosis, not application correctness, and not the Mac/Windows local runtime. The shared task queue in [`coordination/tasks.json`](tasks.json) owns all task state.

## Established evidence (GitHub connector)

| Actual run | Observed job | Recorded outcome | Execution steps shown |
| --- | --- | --- | --- |
| [Shared project loop, main #39687645483](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39687645483) | `coordination (ubuntu-latest)` job **119525663486**, macOS **119525663825**, Windows **119525663844** | All three `completed/failure` | All have `steps: null` in run-job listing; no actual `Set up job` evidence |
| [Business operations, main #39687645556](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39687645556) | Ubuntu **119525663552**, Windows **119525663894** | Both `completed/failure`; downstream report skipped | `steps: null`; report skip is **not** success |
| [Remote handoff, main #39687645548](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39687645548) | Remote work snapshot job **119525663465** | `completed/failure` | `steps: null` |
| [PR #24 original hand above prop #39683961823](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39683961823) | Ubuntu **119513180723**, macOS **119513181190**, Windows **119513181277** | All `completed/failure` | No steps returned; previous job-log download returned HTTP 404 with Azure `BlobNotFound` |
| [PR #21 true wrist raster #39681169031](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39681169031) | Ubuntu **119503711499**, Windows **119503712089** | Both `completed/success` | Actual `Set up job`, checkout, Python installation and 103 test pass were recorded |
| Same PR #21 run | macOS job **119503711958** | `completed/failure` | `steps: null`; cannot establish a failed Python test |

These examples cross **unrelated workflows on main**, PR branches, **three OS choices** and jobs that previously executed. This is not evidence of one failing animation assertion or one broken `pytest` step: no step execution is visible for the latest failures. Equally, these signals alone do **not** prove a specific runner provider, code configuration, budget, or account cause.

### Public platform status (separate source; correlation, not attribution)

[GitHub Status — October 21, 2026](https://www.githubstatus.com/) acknowledged degraded GitHub Actions and delays affecting workflow status updates that day. Its updates report recovery around **16:57–17:09 UTC** and note backlogs. The newer ROVOR failures were created around **22:35 UTC**—later than that recovery report. Therefore the public incident is relevant historical context, **not a verified root cause of those later failures**. October 19 also had a separate resolved incident.

GitHub's own [Troubleshooting workflows](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows) includes guidance on review of Actions billing/usage, runner issues, workflow permissions and contacting GitHub Support. We have **not inspected account billing, current paid-minute budgets, repository-level Actions permissions, abuse limits, job-level annotations, or platform service-internal errors**; each remains unknown. Do **not** infer the user needs a paid plan, payment-method change, or additional minutes.

## What could not be established through connected GitHub tools

- The jobs listing contains `steps: null` on these failed jobs; the separate job-step lookup returned an empty list for PR #24.
- PR #24 failed-job log downloads returned `BlobNotFound`, so there is no readable Python traceback, workflow setup log or supported assertion failure to diagnose.
- The accessible connector does not expose the failing jobs' top-level Actions warning/annotation text, runner provisioning telemetry, or the billing/account authorization screens.
- No new workflow rerun was requested. Repeated retries while the reason is unknown would add cost/queue activity without producing better evidence.

## Minimum-cost unblock procedure for the repository owner

1. **Open the latest failed `main` run**: [Shared project loop #39687645483](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39687645483). Look above the jobs for a run-level red/yellow message or an annotation such as an Actions restriction, service error, runner shortage, or budget warning. Open a failed job and check whether `Set up job` exists. Record the **exact text** and time (without tokens, account secrets, or private artifacts). If there is an actual step and traceback, the problem is a normal test/configuration failure and should be fixed as such.
2. **Check the correct repository-owner Actions settings** in GitHub's website (repository **Settings → Actions → General**), and check the account or organization **Billing/Usage → Actions** information for warnings, remaining allowance, or an execution block. Only report a quota/budget/billing reason after the page actually confirms it; **do not add a payment method, increase spending, or purchase minutes automatically**.
3. Compare the failure timestamp to [GitHub Status](https://www.githubstatus.com/). If the site or job annotation indicates a GitHub service issue, record it. If all three OS jobs fail before any step with no actionable account warning after GitHub reports recovery, use [GitHub Support](https://support.github.com/) with repository, run IDs and job IDs from the above table; request their runner-dispatch diagnostic. Do not submit credentials or private MP3 artwork.
4. **After resolving or identifying the pre-run blocker**, initiate just **one** deliberate test of an existing small workflow (e.g. the shared project-loop validation) rather than rerunning the entire animation stack. Verify it actually recorded `Set up job`, successful Python tests and downloadable logs. Then recheck the existing PR #21 and #24 heads (if the underlying head has changed, run the exact latest version); investigate any **real** code/test failures that now appear.
5. Keep all unfinished claims/draft PRs blocked until their own exact-head checks finish. Reuse passing prior-head evidence only for *unchanged* files/tests and name the previous SHA. No blanket `continue-on-error`, no disabled checks and no invented green status.

### Safe fallback when runners are unavailable

- An authorized human or computer-use execution session with the **actual local checkout** can run the existing standard-library coordination validation: `python tools/project_loop.py check`.
- For the optional source-rig/video tests, use the branch checkout containing the code and genuine registered source art, a compatible Python/Pillow/NumPy/OpenCV environment, and `cd evan-engine && python -m unittest -v test_grip_raster_qa test_right_hand_grip test_directed_paint test_directed_contact_lock test_directed_contact test_directed_scene`. PR #24 adds `test_directed_grip_occlusion` but remains dependency-blocked on PR #21; include it only when testing the draft branch.
- Record commit, OS, Python/package versions, exact command, exit code, output/test count and relevant artifacts. **These local commands have not been run by this investigation**. Do not describe this fallback as completed validation.
- With no original approved roller/wall/Evan project MP3 and actual render host connected, **the final 30+ second real painting movie remains unrendered/unapproved**.

## Evidence required to close this diagnostic task

This investigation can **complete as evidence and an actionable unblock**, without falsely marking GitHub Actions or the animation PRs repaired. Mark operational runner restoration only after a workflow on the current head reports actual steps and successful tests. If a setting, GitHub Service incident, or support notice confirms the root cause, update this document with the exact evidence. No task or PR is automatically approved by this report.
