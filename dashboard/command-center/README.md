# ROVOR Command Center — live GitHub HUD

## Workforce Control HUD — first implementation

A new **ROVOR Workforce Control** module is available at `/workforce/` (also `/?workforce=1`). It shows Walter, Mike, Jane, Jesse, Gale, Gus, Saul and Hank, plus the source-verified development task queue, model-router overview, mission timeline, results and Mac connection status. It supports full HUD-style scrollable panels and local job draft copy/export. **It does not claim any employee is online or permit actual dispatch** until a private authenticated host/controller proves worker receipts and STOP/approval capabilities. The primary native v8.9 visual HUD remains the default.

Source and next integration milestone: `design/hud/WORKFORCE_HUD_IMPLEMENTATION_CHECKPOINT.md`. The public GitHub development queue is not the private SQLite worker job queue.

---


## Current default: Native HUD v8.9 (scrollable instrument previews)

The default GitHub Pages route now redirects to `./native-v8-9/`. This release preserves the original layout while making the six compact instrument panels **independently scrollable**. The active-task card initially shows all verified unfinished tasks and includes an **OPEN / ALL** switch to browse the complete verified archive without expanding. Overflowing cards show a small blue **SCROLL ↓** cue, which disappears at the bottom. Real task rows remain at least 40–44px tall rather than compressing into unreadable lines.

Expanded modules now remain within the same blue/angular HUD visual system. They support Escape-to-close, keyboard focus, and returning to preserved preview scroll positions. Counts and labels are never fabricated; the GitHub queue and routing remain commit-pinned and source-verified. The source currently has 104 tasks (15 unfinished), but the app displays actual values at refresh rather than hard-coded numbers.

Rollback without a force push: `./native/` is the previous deployed v8.5 native build, and `./exact/` is the preserved pixel-reference build. Change the early redirect in `index.html` if reverting default behavior is necessary.

QA: Chromium tests exercised four screen categories with a representative 104-task queue, confirming true overflow, OPEN/ALL filtering, touch-height rows, navigation/expanded views, refresh preservation and no runtime errors. Native Safari/iPadOS rendering is not independently certified. Browser integration checks use mocked GitHub API results.

---


## Native HUD v8.8 — genuinely scrollable mini instruments

The compact panels **scroll their real content within the frame** instead of compressing it or requiring the user to open the focus view. When the queue is verified, Active Tasks shows an **OPEN / ALL** switch: OPEN lists unfinished tasks, ALL includes completed/archived tasks. Recent Activity shows the full timestamped queue history. Workload now includes real priority groups; System Health includes actual source-backed task counters; API Quota and Source Feed display measured GitHub/session details (no invented Mac usage).

Only panels with actual overflow display a noticeable **SCROLL ↓** tag at the **bottom-right**. Touch pan, mouse wheel, trackpad and keyboard scrolling all act on the inner preview. The indicator disappears on reaching the bottom; source refresh preserves scroll positions. Without source data, cards explicitly show unverified state rather than fabricated scrollable history.

Browser tests verify a 104-record queue (15 unfinished, 89 complete), the OPEN/ALL switch, bottom-anchored indicator, independent scrolling, and other interactions across iPhone, iPad portrait/landscape and desktop. No additional API polling, Mac worker claims, or changes to the preserved `/exact/` rollback.

## Prior release: native HUD v8.7 — scroll affordance and refresh stability

Each compact instrument now shows a small blue downward cue only while content remains below its scroll viewport; the cue disappears at the bottom. GitHub refresh keeps scroll position for all six panes, including quota and source details. The centered cinematic focus state, real data verification, portrait/landscape geometry, and prior /exact/ rollback are unchanged.

Browser QA with mocked GitHub responses covered a 29-task queue, three viewport shapes for overflow cues and scroll preservation during refresh, plus desktop/tablet/phone interaction regressions. No additional network polling or privileged Mac actions were introduced.

## Previous release: native interactive HUD v8.6

The six compact home panels are miniature scrollable instruments: real queue/activity rows can be scrolled in place (no forced entry). Header expand controls open a centered neon instrument workspace that uses the same blue frame and keeps the reactor visible behind the scrim. The old edge-to-edge drawer is replaced. Desktop, iPad portrait/landscape and iPhone browser tests ran with mocked GitHub data including a 26-task queue and confirmed scroll positions survive module entry/exit. The live GitHub/source state remains read-only and is never mistaken for Mac runtime state.



The main GitHub Pages URL redirects immediately to `./native/` — the **self-contained native v8.8 build** with real HTML/CSS/JavaScript interactions, embedded Earth/ROVOR artwork and the corrected reactor heading (no `.top-glyph`). This is a tested standalone prototype published as the live default at the user's request.

The prior pixel-matched, image-based HUD remains at `./exact/` for a non-destructive rollback. The older first-generation CSS cockpit source and tests are also preserved. **Do not remove `exact/` without an explicit request.**

All embedded visual resources are included in `native/index.html`; external GitHub information still requires a network connection and remains labeled as verified/unverified. GitHub deployment checks assert one valid native script, embedded assets, absence of the faulty glyph and preserved rollback route. No Mac worker connectivity or private system health is implied.

### Rollback

If the new native build fails, edit `index.html` to redirect `./exact/` again. You can always access the old version directly at `/rovor-video-engine/exact/`.

---

## Default screen: pixel-matched original HUD (October 24, 2026)

*Historical section below describes the prior exact-reference default (now preserved as the rollback).*

**The main GitHub Pages address now opens `./exact/` by default.** The older CSS approximation is no longer the default. This preserves the user's original reference artwork, including its precise ROVOR emblem, planetary Earth, neon angular frames, labels, and navigation at native 1672×941 ratio. It is the existing, interactive `exact/` build, **not** a newly generated graphic.

- On desktop widescreen the reference fills the screen at its natural ratio. Click pictured task panels, system gauges, camera area, logo, or bottom nav to open working inspector/command panels; ⌘/Ctrl+K opens commands; Escape closes; **I** toggles 1:1 immersive mode.
- The same browser session verifies public GitHub task and route files against a single resolved SHA. A screenshot's rendered 12 tasks, 99% uptime, 98% quota, and green sample statuses remain artwork **only**, not verified live measurements. The inspector explicitly shows real source state or UNVERIFIED.
- `exact/` now includes its own scoped static-only PWA manifest and service worker; it never caches GitHub API requests or task/routing responses.
- The old CSS-oriented cockpit is preserved in `index.html` solely as an emergency rollback and regression fixture. The early redirect prevents its scripts/styles from displaying on the main route.


## Electric-blue-only visual theme

The public HUD uses icy white, electric blue, steel blue, and deep navy. **No green, teal-green, yellow, orange, or red status lights** are intentionally displayed. A verified/live connection glows bright blue, pending/ready is medium steel blue, and blocked/error is identified by an explicit label with a pale outlined or dashed marker (not only by color). This change is presentation-only: GitHub data, freshness warnings, task semantics, API request budget, and unattended-worker security boundaries are unchanged.

`electric-blue-theme.css` loads **after** all existing styles and is precached in the v7 offline shell. The source-backed visual states remain legible and distinguishable without the green status dots in the initial screenshot. If data is stale, its text still reads HISTORICAL/OFFLINE; blue styling does not change its meaning.


This is an actual static browser dashboard, not a static mockup. It reads **public** source data from `TeamRovor/rovor-video-engine` and requires no secrets, extensions or server-side access.

## Reference-accurate widescreen cockpit

The first desktop/tablet landscape screen now uses a bounded, near-16:9 HUD composition: framed top header, verified source-status strip, left task/workload/activity cards, large orbital Earth/core, right health/analytics/source cards, bottom five-button dock, and engraved footer. The old, long scrolling reports are not placed below the cockpit on desktop; selecting a bottom tab opens an interactive workspace above it, and **Back to HUD** returns to the main view. Phones retain a vertically stacked layout.

To preserve operational integrity the displayed values are **live public GitHub queue and routing data, when verified**. Resource bars display task distribution rather than fabricated Mac CPU/GPU load; system health denotes routing coverage, not overall private Mac uptime. Source Feed shows an Earth-at-night image as an illustration, accompanied by the real commit/status; it is **not** presented as a live camera.

The 3D-look ROVOR emblem is drawn with a metallic CSS mask using the real logo SVG; it remains the working command-console button. The animated Earth remains controllable and respects reduced-motion settings. The header's **Tools** menu contains the existing refresh/export/focus/motion/fullscreen controls, and the bottom dock opens interactive data workspaces. Browser tests verify the displayed status changes appropriately when the source falls back to a historical snapshot.

## Cinematic interactive HUD (orbital Earth build)

This build renders a **slowly rotating Earth and lower horizon** in WebGL using bundled NASA Blue Marble natural-color satellite imagery and NASA's Earth-at-Night city-light mosaic, instead of the previous low-detail procedural continent blobs. The images are downloaded and validated at *deployment time* into the static GitHub Pages artifact; browsers load them from the same ROVOR site, not from a remote image CDN. The globe is a visualization, **not** a live Earth satellite feed. The canvas is bounded in resolution, frame-capped (~24 fps), and pauses animation on reduced-motion preference, tab suspension or the existing Motion: Off toggle. If image assets or WebGL are unavailable, the original procedural/static fallback remains usable.

The central ROVOR logo is an actual **Command** button. Press it, or press **⌘/Ctrl+K**, to search tasks, switch views, refresh GitHub or export a JSON snapshot. Use **1–5** for dashboard navigation, **?** for keyboard help, or Esc to close. Task and system cards open source-grounded inspectors; queue status bars are clickable filters. The orbit can be **dragged horizontally** or controlled using **Earth · Slow/Normal/Fast**, **Pause Earth**, and **Reset**. Fullscreen is exposed where the browser permits it.

These are browser-only controls, never Mac remote execution. Task owners remain *claims*, and system categories remain *GitHub-sourced descriptions*, not live pings. Earth animation requires no paid server, credentials or third-party asset CDN. GitHub polling and the existing data integrity boundaries remain unchanged.

### Earth imagery attribution / reproducible build

- **Day surface:** NASA/GSFC Scientific Visualization Studio, [Blue Marble](https://svs.gsfc.nasa.gov/2915), based on Blue Marble imagery by Reto Stöckli (NASA/GSFC), NASA's Earth Observatory.
- **Night lights:** NASA/GSFC Scientific Visualization Studio, [Earth at Night](https://svs.gsfc.nasa.gov/2916), imagery by Craig Mayhew and Robert Simmon, based on DMSP/OLS city-light observations.
- `tools/prepare-earth-textures.sh` validates expected PNG file dimensions and signatures. GitHub Pages builds fetch the map files before packaging, and the offline service worker caches the published maps. A local checkout can run the same script before testing the realistic globe. The fallback works without image files.
- NASA imagery is used as Earth visualization data, with no implication of NASA affiliation or endorsement.

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
