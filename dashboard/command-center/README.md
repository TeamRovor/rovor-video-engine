# ROVOR Command Center — live GitHub HUD

This is an actual static browser dashboard, not a static mockup. It reads **public** source data from `TeamRovor/rovor-video-engine` and requires no secrets, extensions or server-side access.

## Reference-style interactive command deck (October 23, 2026)

The command deck is **real HTML/CSS/JS**, not a generated screenshot. Its top screen follows the supplied blue orbital HUD reference: left task/evidence rails, a central animated ROVOR reactor, right routing/repository telemetry rails, and a five-view dock. All panels re-render from the same GitHub source state as the existing detailed workspace.

- Click a task row to open and filter its actual task record. Use Dashboard, Tasks, Systems, GitHub, or Workers to switch detailed views; the lower workspace retains the existing search, status filter, routing and worker information.
- The task workload bars represent GitHub queue **statuses**, not computer resource utilization. “Claimed” means the queue records an owner, **not** that an autonomous worker is currently running.
- Routing health is measured from current task-routing coverage, **not** invented 99% host uptime. Real CPU/GPU utilization, camera feeds, model API quota and remote Mac execution are unavailable in this public read-only dashboard and are deliberately **not faked**.
- “Verified activity” shows source SHA, last verified sync, PR count and snapshot timestamp, not fabricated render-complete events. It clearly marks historical fallback or failed verification.
- Motion and Focus controls still work; reduced-motion settings are respected. The iPad landscape composition and single-column mobile layout remain interactive. Public source refresh remains 3 minutes while the tab is open; the service worker caches only the shell.

## What updates automatically

- GitHub `main` HEAD is checked every **3 minutes while this page is open** and when you return to the tab after a long pause. Each poll reads the task queue and capability routing JSON pinned to **the same SHA**, preventing mismatched moving-branch reads.
- Open PR count and repository file map are checked at most every **15 minutes** to reduce unauthenticated REST API traffic. They can briefly lag behind task status and are identified as supplemental data.
- Current counts, all tasks, statuses, owners, dependencies, routing coverage, and worker *claims* are derived from the current queue, not hardcoded. The worker list is **not an online-presence monitor**.
- The **Refresh GitHub** button requests the current pinned queue and route again. The **Export JSON** button exports current data, together with whether it was live or a fallback.

## Failure visibility and privacy

When GitHub cannot be reached or a critical file fails to load, the dashboard displays **OFFLINE SNAPSHOT** or **SYNC FAILED**, not LIVE GITHUB. Its bundled `snapshot.json` is an older **historical fallback only**, not a live cache. Missing/routing-extra rules are reported as a warning rather than hidden.

**No GitHub token is stored in the browser**. The dashboard can read only data public on GitHub. Do not include unpublished client files, credentials, proprietary media or a private computer's state in this public repository. GitHub REST's unauthenticated IP rate limit can affect refreshes; optional calls are throttled.

Whimsical is a separate visual architecture board, **not automatically synchronized** by this HUD. Native Mac, Windows, Moho, Blender, Final Cut, local job execution and social posting are likewise **not enabled** by this dashboard. A merged test is not evidence that an actual worker is online.

## Live Command Center and iPad installation

**Live URL:** https://teamrovor.github.io/rovor-video-engine/

The site is published on GitHub Pages from `main`. Changes to `dashboard/command-center/` automatically trigger a new deployment; verify the latest run in [GitHub Actions](https://github.com/TeamRovor/rovor-video-engine/actions/workflows/deploy-command-center-pages.yml).

1. Open the live URL above in **Safari** on the iPad.
3. Tap **Share** → **Add to Home Screen**. If offered, enable **Open as Web App**, then tap **Add**.
4. Launch the ROVOR HUD icon from the Home Screen. Rotate to landscape for the full command console; portrait is supported for quick checks.

The web-app manifest and service worker cache only the app shell for faster launch and a limited offline fallback. **Live GitHub API/raw data is never cached by the service worker.** When offline or rate-limited, the HUD must show a stale/error state instead of pretending to be live. iPadOS may suspend a backgrounded or closed web app; this version polls every three minutes while open and syncs when you return. It is not an always-running background agent or push-alert system.

## Free hosting with GitHub Pages

The Command Center is static HTML/CSS/JavaScript, so it does not need a paid server or database. This repository now includes `.github/workflows/deploy-command-center-pages.yml`, which publishes only `dashboard/command-center/` to GitHub Pages after changes to that directory land on `main`, or when manually dispatched.

**One-time repository setup is required:** open the repository's **Settings → Pages** and set **Build and deployment → Source** to **GitHub Actions**. The workflow attempts to enable Pages automatically, but repository or organization policy can block that API operation; if the first run reports `Resource not accessible by integration`, set this option manually and rerun the deployment. After setup, changes to this directory on `main` trigger publication, and the successful deployment run reports the Pages URL. No paid Vercel plan is required for this approach; GitHub Pages availability and usage are subject to GitHub's current plan and repository limits.

For local development, from the repository root run `python3 -m http.server 8000`, then visit `http://localhost:8000/dashboard/command-center/`. The browser needs normal HTTPS access to GitHub.

The standalone shell (`index.html`, `styles.css`, `live-data.js`, `app.js`, `manifest.webmanifest`, `service-worker.js`, `hud-icon.svg`, and `snapshot.json`) can also be hosted on another static HTTPS host without a backend. Do not replace the public agency site unexpectedly.

## Offline tests

```
node --test dashboard/command-center/tests/live-data.test.js
node --check dashboard/command-center/live-data.js
node --check dashboard/command-center/app.js
```

Browser behavior was additionally exercised in Chromium using mocked GitHub responses: live state, task counts, task search/status filters, and no page exceptions. This validates front-end behavior, **not** remote production hosting or future unattended synchronization while the tab is closed.

## Parallel ROVOR dashboards

This Iron Man HUD lives under `dashboard/command-center/` to avoid overwriting the separately authored lightweight GitHub-only operations view in PR #73. Both read the same canonical public GitHub queue. Do not treat the alternate user interface as a second task queue or merge over another contributor's in-progress files.
