# Directed scene physical contact preflight

This adds an **opt-in 60fps artwork-contact gate** to the original two-orientation
directed scene renderer in PR #5. Its purpose is to catch a moving illustrated
prop drifting away from the surface it must touch. A storyboard sentence
claiming contact is never considered proof of contact.

## Authoring contract

Include the following fields inside a shot that already has complete keyed
landscape and portrait compositions, registered original image assets and
its normal start/end frame values:

    "requirePhysicalContacts": true,
    "contactConstraints": [{
      "startFrame": 60,
      "endFrameExclusive": 360,
      "tool": {"assetId": "roller", "uv": [0.5, 0.95]},
      "target": {
        "assetId": "wall",
        "segment": [[0.2, 0.1], [0.2, 0.9]]
      },
      "maxGapPx": 12
    }]

This fragment is not a standalone storyboard. Both roller and wall must be
registered source-art PNG layers, each occurring exactly once per composition.
Place the local UV points on the real painted roller tip and target surface,
accounting for transparent image padding. The gate additionally checks that
contact points land on actual nontransparent source PNG pixels (alpha >= 8);
segment contact is tested at the closest source-edge pixel every frame.
The target can also be a single point instead of a segment. The segment type supports rolling along a wall
edge while remaining in contact.

The gate samples **every frame** from startFrame inclusive to
endFrameExclusive exclusive, using source PNG width/height and the actual
scene camera, prop position, scaling, rotation, and opacity controls. Each
portrait and landscape scene is checked independently. maxGapPx must be
finite, positive, and <=32 screen pixels. For action scenes where contact
is mandatory, requirePhysicalContacts fails closed if the list is missing.

Existing scenes without contact constraints remain valid and return zero
contacts checked. Passing old tests does not assert new physical contact.

## Failure modes

A failing frame aborts preflight with the view and offending frame, before
any animation rendering. For example:

    Contact 1: detached portrait prop at frame 137 (21.74px > 12.00px)

The gate also rejects unknown/unregistered art IDs, multiple ambiguous
instances of one contact asset, invalid/nonfinite UV coordinates, zero-length
surface segments, contact intervals outside the shot, permissive tolerances,
fully invisible layer opacity, and an apparently matching contact that lies
on invisible/transparent artwork instead of a drawn prop or surface.

**Important artistic and rig limitations:** UV anchors are authored in
source-image coordinates. The gate checks source-pixel alpha and projected
layer geometry, but does not inspect final rendered image contact, whether
paint appears where the roller travels, or the anatomical quality of an action.
Evan's actor art ID cannot be treated as a real skeleton or hand endpoint:
native Moho bone/hand evidence requires a distinct rig adapter. Never claim these prop-only checks
certify character-to-tool contact or final animation quality.

## Tests and continued integration

Run from the preserved development branch with Pillow and NumPy installed:

    cd evan-engine
    python -m unittest -v test_directed_contact test_directed_scene

The source-free tests cover real registered PNG fixtures, both formats,
actual keyed movement, contact to a surface edge, drifting off the target,
opacity, invalid controls, actor exclusion and legacy backward compatibility.

New scene review evidence should include the original illustration hashes,
calibrated contact UVs, shot/scene IDs and annotated rendered frames. Human
normal-speed animation review remains required before publication.
