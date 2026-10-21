# Non-Moho visible paint trail from actual roller contact

ROVOR's standalone Pillow/FFmpeg animation track can render portrait and
landscape without Moho. This stage makes **paint visibly accumulate on an
actual illustrated wall** as a source-art tool moves on that wall, rather
than suggesting "painting" in storyboard text while nothing changes.

## Opt-in storyboard specification

Inside an existing directed shot that already has original registered
wall/tool PNGs and two independently authored 60fps compositions, provide
a required physical contact with `lockToolToTarget: true` and add the
following to that same constraint:

```json
{
  "startFrame": 60,
  "endFrameExclusive": 420,
  "lockToolToTarget": true,
  "tool": {"assetId": "roller", "uv": [0.50, 0.50]},
  "target": {"assetId": "wall", "segment": [[0.50, 0.20], [0.50, 0.80]]},
  "maxGapPx": 2,
  "maxCorrectionPx": 255,
  "paintStroke": {
    "color": "#e63946",
    "radiusSourcePx": 6,
    "regionUV": [0.15, 0.15, 0.85, 0.85]
  }
}
```

Illustrative source layer names and UVs are **not** a claim that the
private original painting project uses those IDs. The paint must be
authored/calibrated against the original wall and roller plates.

The wall must be drawn **below** the roller in layer order. The target
and tool must each be uniquely registered source-PNG art layers, not
synthetic actor hand bones. `paintStroke` is optional; old scenes
without it render exactly as before.

## Source-space, cumulative strokes

After PR #18 solves the actual 60fps roller-to-wall positions and the
independent PR #14 physical contact audit verifies them, the new
`directed_paint.py` inverse-projects every real screen contact point
into the wall's original PNG coordinates (accounting for wall
translation, scale, camera zoom/pan and rotation). It rejects invisible
tips, out-of-region painting, unsupported paint colors/radii and
non-progressive strokes.

Every video frame composites only the paint deposited **at or before
that frame**, in source-wall coordinates. The paint persists on that
wall through the end of the shot after the roller lifts away, including
if the wall/camera subsequently moves. The wall image and roller art
are never mutated on disk.

Paint is alpha-clipped to the original target PNG, then restricted to
an explicitly authored rectangular UV region. Source-PNG transparent
padding stays transparent. The actual modified wall is composited
under the tool via `DirectedScene.frame()`. Each landscape and
portrait composition independently computes its own motion/paint
path, rather than artificially cropping one 16:9 composition.

The in-memory `PaintTrack` lazily accumulates the mask on forward
frame playback and reconstructs on backward/random seeks, so
frame rendering is deterministic and can resume without keeping
all prior video frames. Only a single painting rule per target per
shot is supported until independently validated multi-stroke
parent/child attachment and layer handling are introduced.

## Test commands and limitations

From the branch working directory:

```bash
cd evan-engine
python -m unittest -v test_directed_paint test_directed_contact_lock test_directed_contact test_directed_scene
```

GitHub Actions tests source-free fixtures on Linux, macOS and Windows,
using Pillow and NumPy. They rasterize true 1920x1080 and 1080x1920
frames and assert exposed original wall pixels before painting and new
paint-color pixels after tool release. They verify the paint stays
attached to a moving/rotating wall, repeatable out-of-order frame
queries, alpha clipping, no source mutation, scene backward
compatibility and failure on invalid paint contact.

**Not implemented or verified here:** real painter original assets,
real Evan articulated hand/grip, physical roller rotation, a full
4:23 MP3-aligned render, natural professional voice acting,
actual visual/storytelling approval, music/SFX or final MP4 exports.
Synthetic tests are a development gate, not a user-approved movie.

## Follow-up

Apply the rule using the existing private original painter, roller and
wall art, calibrate visible UV positions for each 1080p composition,
then render at least 30 seconds of the actual original narration with
the non-Moho renderer. Review actual frame-seam, wall paint appearance,
tool grip, camera and movement at natural speed before publication.
