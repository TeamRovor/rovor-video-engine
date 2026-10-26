# ROVOR HUD responsive layout reference — v8.2

**Status:** The iPhone and iPad portrait layouts from native HUD v8.1 are an approved direction to **preserve**. The landscape design below is a tested reference checkpoint, not an instruction to deploy or replace the current GitHub Pages site.

## Canonical files

The full, editable v8.2 reference project, browser screenshots and source CSS are archived under the user's ChatGPT Library folder:

`/ROVOR Digital/HUD Design References/v8.2/`

The archive `ROVOR_HUD_Layout_References_v8_2.zip` includes `Portrait_Reference_Board.png`, `Landscape_Reference_Board.png`, `RESPONSIVE_DESIGN_REFERENCE.md`, the native HTML/assets, `landscape-reference.css`, and automated browser QA.

This GitHub reference is intentionally **documentation-only**: do not replace the live Pages HUD merely because a visual reference has been saved.

## Approved portrait arrangements — preserve

| Device | Layout | Essentials |
|---|---|---|
| iPhone portrait (up to 699 CSS px) | Full-width reactor, vertically stacked data panels | Fixed five-button dock, safe-area padding, no horizontal scrolling |
| iPad portrait (700–1100 CSS px portrait) | Full-width reactor followed by a 2-column, 3-row panel grid | Gauges stay circular (1:1), dock fixed, scroll area reserves dock clearance |

Acceptance screens: 430×932 and 820×1180. Treat these as guardrails against landscape CSS accidentally squeezing portrait into three columns.

## New landscape reference — v8.2

| Viewport | Composition |
|---|---|
| iPad 1024×768, Air 1180×820, Pro 1194×834 | Full HUD, aligned 3 columns; no panel clipping or off-screen gauges |
| Laptop 1366×768 | Same 3-column geometry with tighter panel spacing |
| Desktop primary 1672×941 | Canonical cinematic composition relative to the supplied ROVOR image |
| Wide 1920×1080 | Same composition, larger gutters and clearer typography |
| Short phone landscape (height below 650px) | Scrollable / stacked layout; never force a compressed full cockpit |

**Landscape layout rules:**
- Grid columns: `minmax(0,1fr) minmax(0,1.22fr) minmax(0,1fr)` — left / center / right.
- Header band: 65–84px; footer: 34–46px. Side-panel rails share deck top and bottom.
- Gaps between rails: approximately 7–15px, responsive to viewport width.
- Center reactor stays dominant; title above rings, tagline above navigation.
- Five-item navigation dock: 66–86px, bottom anchored **above** the footer with 8px buffer. It must **not** cover the motion control or the footer.
- Source task rows must be fully visible; health and quota circles always 1:1 aspect ratio.
- Use dark navy, ice white and electric blue. Do not use bright green status accents.
- Never display fake Mac worker, video-engine, CPU/GPU or API-provider telemetry as live.

## Regression checklist for subsequent versions

Test at 430×932, 820×1180, 1024×768, 1180×820, 1194×834, 1366×768 and 1672×941. Assert: no horizontal overflow; fifth task row visible; circular gauges; dock above footer; reactor motion control unobscured; task/system drawers operate and dismiss; all real GitHub values retain verified/unverified semantics; reduced-motion preference respected. The v8.2 layout passed automated Chromium checks with mocked GitHub responses, **not** physical iOS Safari certification.

**Next revision rule:** preserve the portrait templates; evolve landscape using the same reference board and sizing tokens, not more one-off arbitrary CSS offsets. Do not auto-deploy reference prototypes to the live site.
