# Command Center API budget QA — 2026-10-23

**Scope:** independently validate the already-merged Iron Man Command Center (dashboard/command-center/) without modifying its implementation. The test executes the actual app.js and live-data.js using Node's VM, a fake DOM, deterministic clock and mocked GitHub responses. No public API calls, credentials, or Mac controls are used.

## Acceptance

- Run the actual application boot and automatic polling for 60 simulated minutes.
- Count only requests to api.github.com against the unauthenticated REST budget. Pinned raw.githubusercontent.com JSON reads do not count as REST API calls, but both files must use the same immutable SHA.
- Assert the UI reports live state when critical pinned queue/routing data succeeds.
- Inject HTTP 403 after a configurable REST threshold and assert the dashboard switches to its explicit OFFLINE SNAPSHOT state with a visible sync-failure warning, rather than claiming the old data is live.
- Scan app source for browser credentials and mutating HTTP methods.
- Keep local runtime and deployed browser validation claims separate from this deterministic hosted test.

## Expected traffic model

The implementation checks main HEAD every three minutes and refreshes the repository tree and open PRs every fifteen minutes. The steady-state estimate is about 28 REST requests/hour, with a few additional calls during first load and any manual refresh. The executable test output is authoritative; record the observed count below after hosted CI completes.

## Result

Pending hosted run for this QA branch. This report will be updated with the exact count and any discrepancies after the test executes.
