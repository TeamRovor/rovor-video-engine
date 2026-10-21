# Non-Moho original-art physical contact animation

The ROVOR video engine has two independent output targets: native Moho
as the future Ghost Employee and a standalone original-art
Python/Pillow/FFmpeg renderer that can produce video *without* Moho.
This change improves the latter: an illustrated roller or other prop
can actually track a painted wall/surface on every video frame instead
of drifting off and passing as a false "painting" scene.

## What is implemented

A shot's existing `contactConstraints` may opt into:

    "lockToolToTarget": true

This works together with the previously available
`startFrame`, `endFrameExclusive`, `tool` UV,
`target` UV or target `segment`, and `maxGapPx`
contact audit fields. Optionally specify `maxCorrectionPx`
(bounded to 260 screen pixels), to reject source scenes so far from
the contact surface that an automatic positional repair would be a
misleading scene rewrite.

For example, inside a complete original-art shot:

```json
{
  "requirePhysicalContacts": true,
  "contactConstraints": [
    {
      "startFrame": 0,
      "endFrameExclusive": 480,
      "tool": {"assetId": "paint-roller", "uv": [0.50, 0.85]},
      "target": {"assetId": "painted-wall",
                 "segment": [[0.45, 0.10], [0.45, 0.90]]},
      "maxGapPx": 2,
      "maxCorrectionPx": 255,
      "lockToolToTarget": true
    }
  ]
}
```

This JSON fragment is *illustrative*. The verified original scene art
must actually contain opaque roller contact-tip and target-wall pixels
at those UV coordinates. No art is invented or imported by this code.

## How real rendered frames change

For each independently authored landscape (1920x1080) and portrait
(1080x1920) composition, the solver:

1. Samples the original tool's keyed gesture and stage camera at each
   actual integer 60fps video frame in the shot.
2. Projects the tool's genuine original-PNG contact anchor onto the
   nearest visible source-wall edge, while preserving the movement
   along the edge, tool scale/rotation/opacity, and camera.
3. Corrects only the tool's translational X/Y on the real rendered
   layer. The new per-frame keys are passed into `DirectedScene.frame`
   and the existing independent contact audit before encoding.
4. Rejects the attempted lock if the tool starts far away, the
   correction exceeds a bounded screen-pixel displacement, either
   sprite is invisible/transparent at the contact point, the target
   is unknown/ambiguous, or a lock would teleport on approach,
   release or between attached video frames.
5. Refuses overlapping or chained locks of one tool onto another
   simultaneously locked tool. Such interactions require an
   independently validated parent-child rig rather than guessing.
6. Leaves legacy scenes and original author key arrays untouched
   unless a valid lock has explicitly been opted into.

The solver runs *before* the existing contact preflight so that
preflight verifies the final rendered positions, not the original
detached tool layout. The output tracks are the actual 60fps raster
animation input, not a post-hoc metadata report.

## Regression evidence

GitHub CI installs only Pillow and NumPy and uses registered,
SHA-verified synthetic PNG source-art fixtures from the current
ROVOR directed-scene tests. Tests exercise all-frame prop contact
in both orientations and draw actual 1920x1080 and 1080x1920
raster frames. At the same wall contact point, an unlocked tool
renders the background wall pixel while a locked tool renders the
actual moving sprite pixel. Other tests cover source art hashes,
alpha padding, unknown anchors, independent camera movement,
boundary and mid-contact teleport refusals and backward
compatibility.

Suggested command on the branch:

    cd evan-engine
    python -m unittest -v test_directed_contact_lock test_directed_contact test_directed_scene

There is **no claim** that this produces an approved finished video:
the test PNGs are not the private painting project's real source
plates, Evan's authentic hand skeleton is not contacted by the
solver, and no full original narration was re-rendered. It does
not solve character acting, wrist anatomy, real paint appearing on
the wall, music, native Moho automation, editorial narrative
direction or final 1080p60 cinematic quality.

## Next production step

Apply calibrated contact anchors to the actual original wall,
roller and character illustrations in the painting film. Verify
the motion against the real MP3/WAV, render complete source
portrait/landscape segments with FFmpeg, inspect the results at
normal speed, and secure Amar's artistic signoff before
promoting any video as ready for publication.
