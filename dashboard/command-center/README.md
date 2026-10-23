# ROVOR Command Center — live GitHub HUD

This is an actual static browser dashboard, not a static mockup. It reads **public** source data from `TeamRovor/rovor-video-engine` and requires no secrets, extensions or server-side access.

## What updates automatically

- GitHub `main` HEAD is checked every **3 minutes while this page is open** and when you return to the tab after a long pause. Each poll reads the task queue and capability routing JSON pinned to **the same SHA**, preventing mismatched moving-branch reads.
- Open PR count and repository file map are checked at most every **15 minutes** to reduce unauthenticated REST API traffic. They can briefly lag behind task status and are identified as supplemental data.
- Current counts, all tasks, statuses, owners, dependencies, routing coverage, and worker *claims* are derived from the current queue, not hardcoded. The worker list is **not an online-presence monitor**.
- The **Refresh GitHub** button requests the current pinned queue and route again. The **Export JSON** button exports current data, together with whether it was live or a fallback.

## Failure visibility and privacy

When GitHub cannot be reached or a critical file fails to load, the dashboard displays **OFFLINE SNAPSHOT** or **SYNC FAILED**, not LIVE GITHUB. Its bundled `snapshot.json` is an older **historical fallback only**, not a live cache. Missing/routing-extra rules are reported as a warning rather than hidden.

**No GitHub token is stored in the browser**. The dashboard can read only data public on GitHub. Do not include unpublished client files, credentials, proprietary media or a private computer's state in this public repository. GitHub REST's unauthenticated IP rate limit can affect refreshes; optional calls are throttled.

Whimsical is a separate visual architecture board, **not automatically synchronized** by this HUD. Native Mac, Windows, Moho, Blender, Final Cut, local job execution and social posting are likewise **not enabled** by this dashboard. A merged test is not evidence that an actual worker is online.

## Install on an iPad

1. Publish this directory over **HTTPS** on a stable host. The source change alone does not publish it or enable GitHub Pages.
2. Open the published Command Center URL in **Safari** on the iPad.
3. Tap **Share** → **Add to Home Screen**. If offered, enable **Open as Web App**, then tap **Add**.
4. Launch the ROVOR HUD icon from the Home Screen. Rotate to landscape for the full command console; portrait is supported for quick checks.

The web-app manifest and service worker cache only the app shell for faster launch and a limited offline fallback. **Live GitHub API/raw data is never cached by the service worker.** When offline or rate-limited, the HUD must show a stale/error state instead of pretending to be live. iPadOS may suspend a backgrounded or closed web app; this version polls every three minutes while open and syncs when you return. It is not an always-running background agent or push-alert system.

## Open the dashboard

- If the ROVOR repo has GitHub Pages configured to serve the appropriate directory, use the Pages URL. Merely merging these source files does **not** configure GitHub Pages or deploy a live web address.
- For local development, from the repository root run `python3 -m http.server 8000`, then visit `http://localhost:8000/dashboard/command-center/`. The browser needs normal HTTPS access to GitHub.
- The standalone shell (`index.html`, `styles.css`, `live-data.js`, `app.js`, `manifest.webmanifest`, `service-worker.js`, `hud-icon.svg`, and `snapshot.json`) can be deployed on a static HTTPS host without a backend. Do not replace the public agency site unexpectedly.

## Offline tests

```
node --test dashboard/command-center/tests/live-data.test.js
node --check dashboard/command-center/live-data.js
node --check dashboard/command-center/app.js
```

Browser behavior was additionally exercised in Chromium using mocked GitHub responses: live state, task counts, task search/status filters, and no page exceptions. This validates front-end behavior, **not** remote production hosting or future unattended synchronization while the tab is closed.

## Parallel ROVOR dashboards

This Iron Man HUD lives under `dashboard/command-center/` to avoid overwriting the separately authored lightweight GitHub-only operations view in PR #73. Both read the same canonical public GitHub queue. Do not treat the alternate user interface as a second task queue or merge over another contributor's in-progress files.
