# ROVOR non-Moho original FK wrist-to-tool attachment — experimental

This is a **real joint-control change** to the existing standalone
Python/Pillow/FFmpeg animation pipeline, NOT a native Moho feature.
Existing original Evan raster components, the original 4:23 MP3/WAV,
artwork hashes and all previous non-Moho shots remain untouched.

## Opt-in shot contract

A complete 60fps directed scene with independently authored landscape
1920x1080 and portrait 1080x1920 original art may add one or two
`handGripConstraints` alongside existing, independent prop-to-wall
contact and optional accumulating `paintStroke` constraints.

```json
{
  "handGripConstraints": [
    {
      "startFrame": 60,
      "endFrameExclusive": 200,
      "toolAssetId": "roller",
      "toolHandleUV": [0.5, 0.7],
      "hand": "relaxed-right",
      "maxGripGapPx": 4
    }
  ]
}
```

The tool ID and UV are **illustrative** and must be separately calibrated
on the approved original roller image. The handle UV must point to drawn,
nontransparent source-art pixels; the tool must composite in front of
the real Evan body. The original `rightHandKeys` must select the
existing experimental `relaxed` hand plate throughout the interval.
No new generated drawing, invented wrist or finger anatomy is introduced.

## Actual movement algorithm

- Load the existing original
  `evan-character/cartoon-v1/body-rig/manifest.json`
  shoulder and elbow pivots plus the separate
  `hand-source/manifest.json` relaxed-hand `rigWrist` attachment.
- Derive the genuine right-wrist position from the **same hierarchical
  source FK rotation matrices** already driving `CartoonBody`.
- Account for Evan's existing 220-pixel source pad, 1464x1536 body
  canvas, authored `body_roll`, scene placement, and each output
  aspect ratio/camera. Project the roller's real opaque handle anchor
  into actor source coordinates.
- Require the two independently authored compositions to specify
  approximately the **same hand target** (within 5 source pixels).
  One actor body frame is reused for both views: no dishonest
  divergent hand animation between aspect ratios.
- Apply bounded damped two-link FK shoulder/elbow correction while
  retaining the authored terminal wrist angle, 12/30-degree source
  joint limits, and a 2.5-degree maximum per-frame change. Refuse
  unreachable grips, discontinuous configurations or visible hand
  gaps over the scene's maximum (up to 8 screen pixels).
- Use those corrected original controls in `CartoonBody.render`
  when the actual FFmpeg frame loop runs; no illustration or
  audio source rewriting.
- Disable source-body PNG reuse for shots with grip overrides:
  a previously cached frame lacking the correction must not
  masquerade as the new frame. All earlier non-grip directed
  scenes follow the existing unchanged path.

This stage is **not a true gripping finger articulation**: the
experimental relaxed-right hand has no curlable fingers, and the
original source rig metadata explicitly states animation-ready false
and visualApproved false. The solver pins its original FK wrist
attachment near a tool handle but is not allowed to claim the hand
fully encloses the roller, that the roller follows a physically
verified hand mesh, or that the user approved the final image.

## Tests and release criteria

The new three-platform CI runs the original-hand-manifest source
geometry tests plus all prior directed original-art/physical contact
and visible paint regressions. It checks real 60fps actor-to-tool
projections in both dimensions, bounded FK source joints, non-overlap,
missing provenance, wrong hand pose, detached/unreachable targets,
and backward compatibility. Synthetic source-PNG test actors do NOT
certify visually pleasing real artwork.

Before treating it as part of a publishable painting film, a trusted
host must inspect the original layered hand and roller, calibrate
actual handles and separate wall contact, test every frame of an
original >=30-second real narration segment at 1920x1080 and 1080x1920
60fps, and have the user review its wrist anatomy, visual grip,
roller pressure, painting action, edited staging and English lip sync.

This experimental PR is stacked on PR #19 -> PR #18 -> PR #14 -> PR #5.
Do not independently merge it into main.
