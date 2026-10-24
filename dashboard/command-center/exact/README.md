# ROVOR DIGITAL — Exact Reference HUD

This is the user's requested **1:1 reference-backed interactive HUD**. The `reference.png` asset contains the *unchanged original 1672×941* reference image; it is an illustrative scene, **not real telemetry**. A blue-only alternate image is selectable under Settings, but the default is the unmodified reference. On widescreen displays (at least 1024px wide, 3:2 aspect ratio or wider), immersive **1:1** mode now opens automatically without extra header/footer bars. Press **I** or **Esc** to reveal the normal toolbar; you can re-enter 1:1 mode there. Tablet portrait and phone layouts keep visible controls. The artwork retains its native 1672×941 aspect ratio without stretching.

## Interaction

Transparent HTML controls follow the exact pictured regions (task panels, status cards, ROVOR logo, dock). Clicking them opens a keyboard-accessible inspector with **independently fetched and pinned** GitHub task/routing data. The GitHub HEAD SHA is fetched first and both queue and routes are read at that same commit. Status is explicitly **UNVERIFIED** on failure; Mac/GPU/API quota, live camera, and task execution are not inferred from the reference art. Includes Cmd/Ctrl+K commands, task filters, status drilldowns, exported verified JSON, optional subtle orbit motion, optional green-free recoloring, and responsive mobile controls.

## Security, licensing, source integrity

- Source art was provided in the user conversation and installed without visual modification. Any task counts, 'RUNNING', system health and API quotas printed into the art are EXAMPLE TEXT.
- The browser-side app uses public GitHub read-only endpoints and makes no privileged/native worker calls, API key requests, or paid model calls.
- This alternate HUD does not replace `../index.html` until visual and interaction verification on the actual target Mac/iPad; both remain accessible.
- The exact reference image is retained separately from the dynamic data, so browser overlays never pretend printed figures are real.
- Automatic GitHub sync checks only while the page is visible, no more than approximately every 3 minutes.
