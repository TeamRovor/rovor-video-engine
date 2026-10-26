# ROVOR Workforce HUD — recovered implementation checkpoint

**2026-10-24** — Resumes the OmniRoute / named ghost-employee / interactive HUD work that the user reported as missing from the visible chat history.

## Current work shipped in this branch

- New entry: `dashboard/command-center/workforce/index.html` — HTML/CSS/JS native ROVOR HUD.
- Entry URL once merged: `https://teamrovor.github.io/rovor-video-engine/workforce/`.
- Alternate deep link: `https://teamrovor.github.io/rovor-video-engine/?workforce=1`.
- The normal root URL **still opens native-v8-9**, and `/native/` and `/exact/` remain rollback views.
- Six independently scrollable instrument previews, each with a matching blue angular expanded module.
- Source-verified GitHub development queue with OPEN / ALL and full-text filtering; latest GitHub task-change timeline.
- Eight named charter roles: Walter (supervisor), Mike (Mac systems), Jane (Final Cut), Jesse (Moho), Gale (Blender), Gus (operations), Saul (marketing), Hank (QA). Every runtime status remains **UNVERIFIED**.
- Visible OmniRoute/model inventory cards with **NO LIVE INVENTORY**, not fake model connections or quotas.
- Local-only job composer (goal, employee, deliverable, due preference). Copy/export allowed, **Approve & Queue disabled**. No persistent browser storage or write requests.
- Source verification resolves `main` once to a 40-character SHA and reads the task queue, routing rules, role bootstrap, and provider policy from **the same immutable commit**. Failures remove the verified badge and all stale task rows.
- GitHub polling occurs on load, manual refresh and every 15 minutes only when the tab is visible.
- This is a source-reading UI release, **not** a claim that Mac workers are online, that OmniRoute is serving verified routes, or that a Cloudflare controller is deployed.

## Critical distinction

`coordination/tasks.json` = development collaboration claims. It is NOT the private Mac/SQLite runtime job queue. A GitHub task status `active` is not proof of an active AI inference job. Public GitHub Pages cannot securely connect to `http://127.0.0.1:20128` on a remote Mac, hold model keys, access the user's Keychain, or execute privileged worker actions.

The previous Mac LaunchAgent + SQLite + STOP work, PR #41, OmniRoute experiments and worker workpacks remain the intended runtime foundation; do **not** create a competing scheduler.

## Exact next milestone — authenticated read-only bridge

Before offering a functioning **Queue / Assign / Cancel / Stop** action in the public-facing HUD:

1. Verify the existing Mac supervisor locally on the actual machine: running LaunchAgent, SQLite WAL integrity, STOP state, worker identity and heartbeat, current model inventory, and a new bounded inference canary. Do not replay known-failed job IDs.
2. Implement a private HTTPS **read-only snapshot endpoint**, with a scoped token or authenticated session and authenticated *outbound Mac push/pull*. It should return timestamped receipts; no provider keys, raw prompts, customer files, unrestricted filesystem paths, or fabricated worker states.
3. Suggested minimal redacted snapshot shape:

```json
{
  "schema_version": 1,
  "observed_at": "2026-10-24T00:00:00Z",
  "source": "authenticated_mac_worker",
  "host": {
    "state": "offline_or_online_from_verified_heartbeat",
    "last_seen": null,
    "stop_engaged": null
  },
  "roles": [
    {"id": "walter", "state": "unknown", "last_seen": null, "active_job_id": null}
  ],
  "jobs": [
    {"id": "opaque_job_id", "role": "jesse", "state": "needs_review", "updated_at": "2026-10-24T00:00:00Z", "receipt_id": "opaque_receipt_id"}
  ],
  "routes": [],
  "quota": {"remaining": null, "verified_at": null},
  "permissions": {"can_enqueue": false, "can_approve": false, "can_stop": false}
}
```

4. Validate stale heartbeat and uncertain states as OFFLINE/UNKNOWN, not RUNNING. Signed/authorized source, strict schema, bounded pagination, no secrets in response, and caching disabled for runtime snapshots.
5. After read-only telemetry is proven, wire a **private, authenticated review-to-queue transition** that checks: explicit user authorization, capability/role eligibility, unique dedupe key, machine STOP, safe input scope, actual provider eligibility, rate/cost bounds, atomic SQLite claim and durable receipt. A failed or uncertain side-effect must not be auto-replayed.
6. Only after the above controls are tested: expose **Approve & Queue**, **Hold/Cancel**, **STOP** with real acknowledgements. The UI must never claim success before the backend supplies a durable receipt.

## Design requirements preserved

- User-approved portrait layouts and 3-column landscape geometry from `design/hud/RESPONSIVE_LAYOUT_REFERENCE_v8_2.md`.
- Neon-blue + white dark palette, NOT green accents.
- Compact card scrolling plus native expanded focus views, not a generic full-screen plain app.
- Precise Earth/ROVOR visual remains in main native HUD; workforce is an operations module, not a forced replacement of its home screen.
- First-party **Open Interpreter** host control must remain an option only once Mac permissions and native GUI capability have been verified. Do not assume Final Cut, Moho or Blender automation works merely because commands were written.
- Default inference/spend posture: verified $0 route only, privacy guard, explicit owner opt-in for any paid model; do not silently charge or transmit client secrets.
- Actual background autonomy needs scheduled host/cloud process + verified two-cycle repeat/recovery; an open ChatGPT message cannot supply 24/7 execution by itself.

## QA

`node --test dashboard/command-center/tests/workforce-control.test.cjs`

The PR and Pages release workflows include this test. The initial phase is deliberately **read-only public source + local draft export**.
