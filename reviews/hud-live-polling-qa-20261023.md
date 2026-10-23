# Independent HUD public API budget review — 2026-10-23

**Source under review:** [draft PR #73](https://github.com/TeamRovor/rovor-video-engine/pull/73), `dashboard/index.html`, head `166c1c23f17188a97a53359470d10c62ae277a50` at initial review. This document belongs to a separate QA task; it does not take over the dashboard owner or modify the HUD's source.

## Verified call model before runtime test

The current browser `sync()` issues three unauthenticated GitHub REST requests per refresh: `commits?sha=main`, then two contents API requests for queue/routes. It also calls `pulls?state=open` on the initial load and approximately every five minutes.

The current timer is 60 seconds, so a continuously open tab performs roughly **180 core REST calls/hour plus 12 PR calls/hour (about 192/hour)**, before any manual refresh. GitHub's standard unauthenticated REST allowance is **60 requests/hour per IP**, a shared allowance. This makes the proposed long-lived self-updating HUD structurally unreliable in its present draft form, even if its data presentation and pinned revisions are correct.

The test `tests/test_hud_live_polling_budget.js` runs the **actual inline dashboard script** inside an isolated Node VM with a fake DOM, deterministic clock and mocked GitHub HTTP responses. It checks pinned queue/routing reads, counts automatic calls across 60 simulated minutes, injects HTTP 403 after 60 calls, checks that the displayed status fails closed, and scans for mutating methods/secrets. No real token or API request is required.

## Required acceptance for PR #73

- Bring normal unattended GitHub REST usage **below 60/hour**, preferably with enough headroom for other apps and manual refresh. A possible implementation is one HEAD/revision request every ~3 minutes, fetch both JSON files via `raw.githubusercontent.com` pinned to that SHA, and query PRs no more than every 15 minutes. Calculate and test the actual method implemented rather than merely trusting this suggestion.
- Keep the task and routing JSON on one immutable revision; do not silently mix `main` contents across separate reads.
- A GitHub 403, network interruption, invalid file or API budget exhaustion must display an explicit stale/error state. The worker's GitHub task claim must never be represented as verified online Mac execution.
- Do not add public browser credentials or enable execution endpoints.
- Re-run the independent simulated full-hour test and verify a real browser refresh before merging as a finished, automatically updated HUD.

**Scope limitations:** A mocked-browser test is evidence for client request scheduling and error display, not proof of production hosting, private Mac control, or actual overnight unattended synchronization while the tab is closed. The owner of PR #73 retains responsibility for fixing the dashboard code.

## Observed hosted baseline — 2026-10-23

- Run: [39912037508](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39912037508), tested the PR #73 merge ref at HUD head `166c1c23f17188a97a53359470d10c62ae277a50`.
- Result: **3/4 tests passed; the budget acceptance failed** with `HUD used 194 unauthenticated REST calls in 60 min`, against the 60/hour ceiling. The immutable-SHA test passed. The injected-403 test passed and confirmed the UI changes to `STALE / ERROR` with a visible sync-failure notice. The no-token/no-mutation scan passed.
- This is a deterministic mocked-browser CI run, not a measurement from a deployed browser or real public API.
- The initial static estimate is approximately 192 requests/hour; the actual simulated count of 194 is the controlling test result and reflects timer scheduling at the test boundary. The fix must be validated against the executable test, not the estimate.
- An actionable release-blocker comment was posted on PR #73 (comment ID `6358993663`) with the result and a lower-call strategy. Dashboard implementation remains the PR owner's responsibility.
