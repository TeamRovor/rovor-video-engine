# ROVOR non-Moho original Evan hand-over-tool foreground compositing

The non-Moho renderer previously flattened Evan into one RGBA actor layer
and drew the roller after the actor. This hides the whole original hand
behind the roller, even after mathematical FK right-wrist-to-roller contact
passes PR #20 and real wrist raster presence passes PR #21.

This experimental branch performs a **different, visible compositing step**:
the actual original registered relaxed-right hand plate is drawn *above the
held prop* while Evan's main body and sleeve remain underneath it. The
forearm, hand position, and angle all use the **same source FK joint controls**
as the original actor and pass through the same 1464x1536 actor canvas,
220-pixel source padding and original body roll.

## Implementation

- `evan-engine/directed_grip_occlusion.py` loads only the source-registered
  `cartoon-v1/hand-source/relaxed-right-v1.png`, with the existing
  `WristPlate` transform calibrated from original shoulder/elbow/hand
  metadata. It does **not** invent another drawing, generate a new avatar,
  alter the source image or use Moho.
- For each `handGripConstraints` shot already validated by the original
  FK solver, it binds the exact already-verified tool asset ID, integer
  frame and single authentic right-hand pose. The same object renders
  a bounded last-frame cached RGBA overlay shared between portrait and
  landscape frame production, rather than creating a different hand
  for each aspect ratio.
- `DirectedScene.frame` paints the original body in back, then the held
  roller, then the registered right-hand foreground pass at the **actor's
  same stage/camera/opacity transform**. Other separately authored
  foreground layers remain later in the layer order. The paint deposited
  on the wall is still drawn behind the roller and hand.
- Unopted scenes do not load or draw a foreground hand. Original audio
  files, hand illustration bytes, source scene keys, main branch and
  connected Windows workstreams are not changed.

## Raster-level development regressions

`evan-engine/test_directed_grip_occlusion.py` uses actual layered
`CartoonBody.render` artwork with a real source `WristPlate` and a
registered synthetic prop fixture. It compares actual 1920x1080 and
1080x1920 rendered pixels at the contact point with the overlay enabled
and disabled, confirms that alpha is nonempty, prevents source art
alteration and path escape, tests before pickup and after release, and
ensures legacy scenes remain unchanged.

Run from the `evan-engine` directory:

    python -m unittest -v test_directed_grip_occlusion test_grip_raster_qa test_right_hand_grip test_directed_paint test_directed_contact_lock test_directed_contact test_directed_scene

## Current verification limitation

This branch is **draft and NOT ready to merge**. On 2026-10-21 GitHub Actions
marked the new and unrelated inherited directed-scene workflows failed,
but their job-steps responses were empty and log-download redirects
returned `BlobNotFound`. That prevents a meaningful determination
of whether failures are runner infrastructure or source/test code.
No local execution of the private original art tests was possible in
this environment. Do not assert success until reliable test
execution/logs exist, errors are fixed, and all three OS targets pass.

The Mac-hosted checks for prior draft PR #21 were also stuck queued.

This is a *foreground occlusion improvement*, NOT a proven anatomical
closed grip: the original relaxed-right hand drawing remains
experimental and not visually approved; visible fingers wrapping the
roller, natural palm angle, wrist anatomy and painter staging still
need direct normal-speed review on the original painting source.

No real 4:23 narration, original painting footage, native Moho
application or full 1080p60 MP4 output was used in this implementation.

## Next acceptance gate

Restore reliable CI runner/log access. Fix any failed tests, then
render a long-enough actual narration scene using original Evan,
roller and wall artwork in both 1080p60 formats. Visually inspect
hand/tool depth, progressive paint, English lip synchronization,
spatial staging, rolling motion and camera continuity; refine
source hand art if needed before artistic approval.

Dependency stack: PR #24 -> #21 -> #20 -> #19 -> #18 -> #14 -> #5.
