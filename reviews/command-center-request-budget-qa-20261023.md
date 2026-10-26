# Request budget QA — real merged ROVOR Command Center
Date: 2026-10-23, independent QA lane.

The **old, separate lightweight dashboard draft** in PR #73 consumed **194 simulated REST requests during an hour**; [run 39912037508](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39912037508) is an intentionally failing release gate for **that** old draft. Do not confuse this with the separately merged blue/orange Iron Man Command Center [PR #76](https://github.com/TeamRovor/rovor-video-engine/pull/76).

The merged Command Center lives at `dashboard/command-center/`. It checks the current GitHub `main` commit every **3 minutes** while its tab is visible, fetches task/routing JSON from immutable SHA-pinned raw GitHub paths, and checks two optional REST sources (open PRs and tree/file map) no more often than every **15 minutes**.

Expected REST usage for one continuously visible dashboard instance during 60 elapsed minutes (including initial fetch and the t=60 check): **21 HEAD lookups + 10 supplementary calls = 31 REST calls/hour**. Approximately 42 raw file fetches are not GitHub REST API calls. This is below the normal anonymous REST cap of 60/hour/IP, with headroom for manual refreshes.

The new test `dashboard/command-center/tests/request-budget.test.js` runs the **actual merged app.js** in a mocked-document Node VM, exercises a deterministic 60-minute foreground tab, asserts pinned queue/routing revision and correct LIVE status, checks visibility pause and manual refresh, and examines for browser write credentials. No live API access is needed for this CI test.

**Remaining limits:** The anonymous REST limit is per shared IP, not per tab. Two simultaneously visible dashboards on the same external IP could exceed the 60/hour allowance (2 × 31 = 62, before other tools). The existing visibility pause reduces normal exposure; a genuinely multi-device always-on view would need additional shared caching/server-generated public status snapshots or a slower cadence with more headroom. This QA verifies a **single active visible client**, not many simultaneous machines, background execution, native Mac control, or hosted production access.

## Hosted result

- Run: [39913559189](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39913559189).
- **Observed: 31 GitHub REST requests and 42 pinned raw reads in 60 simulated minutes.**
- All six tests passed: exact-SHA queue/routing reads, hourly REST budget, hidden-tab pause, manual refresh limits, no credentials/mutating methods, and explicit stale-snapshot downgrade after a failed critical refresh.
- This validates the current merged Command Center source at the PR merge ref using mocked responses. It is not a live API, deployed browser, or local Mac test.

Keep the lightweight HUD QA for PR #73 separate; its revised head now passes at 32 REST requests/hour. The tested Command Center source lives on main under dashboard/command-center/; don't overwrite it with PR #73.
