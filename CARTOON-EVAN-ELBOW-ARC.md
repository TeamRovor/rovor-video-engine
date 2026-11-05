# Evan cartoon elbow material study

The existing right-arm linear blend reverses painted cuff triangles during a large raised-arm pose. `ElbowArcReview` is an opt-in construction study using the existing separated right-arm material. Current speaking scenes do not import it.

A finite-radius centerline spreads elbow curvature over 220 source pixels along the actual elbow-to-wrist axis. Cross-sections follow the curve normal; upper material outside the bend stays on the shoulder parent and distal material stays rigid with the forearm. This is a continuous mesh deformation of the arm component, not a flattened character or head swap. Existing mesh rasterization and premultiplied source pixels are reused unchanged.

The initial study used shoulder −5° through 0°, elbow −135° through 0°, wrist fixed at zero. The initial study rejected unsupported poses. The curved centerline moves the distal anchor relative to the old hinge FK; its old hand-parent matrix cannot be reused. That initial study claimed no independent wrist, new hand attachment, pose switching or finger articulation. The current independent-wrist extension is documented in CARTOON-EVAN-ARC-WRIST.md.

## Comparison and checks

Local outputs: `outputs/evan-cartoon-cuff-forearm/` from the workspace root. `Normal.mp4` and `Slow.mp4` compare actual old/new arm material at native scale. `Stage-Normal.mp4` and `Stage-Slow.mp4` place the candidate in the existing official Rovor stage. Each normal film has 96 frames at 48fps; each muted quarter-speed film has 384 frames. All four fully decode. The stage's other character layers and presentation are held; there is no narration synchronization or speech-profile change.

Across the 96-frame sweep, candidate minimum signed triangle area2 is 140.474429607072; existing LBS has 56 fold frames. Three focused tests cover 408 combinations of shoulder/elbow angles, rigid distal material, unchanged upper material, exact neutral geometry, pixel-exact neutral composition on the padded body canvas, source preservation after rendering and invalid pose rejection. Geometry checks do not establish anatomical or acting quality.

All 96 native cuff crops were inspected in six contact sheets, plus native mid/raised whole-arm comparisons and full-stage mid/raised frames. The candidate keeps the cuff connected and avoids the collapse seen in the old raised pose. The inner cuff still develops a pointed notch and compressed fold shading; the hand drawing remains fixed and the body/face remain held. This falls short of the expressive acting and useful hand poses in the design sheet. Anatomy, final animation and production integration remain unaccepted.

## Rejected constructions

A two-rigid-plane ownership split at axial cuts −20, 0 and +20 conserved the neutral source exactly, but all three showed a fading cloth tail, doubled cuff material or exposed cut at mid/raised poses. These are runtime ownership masks, not source-alpha cleanup. All are rejected and kept only as frozen local reproductions.

A 160-pixel finite bend removed many problems but still reverses one retained grid triangle at the raised endpoint (minimum area2 −17.595263706159585). Do not weaken the structural guard because that cell might be empty. The selected 220-pixel construction remains positive over the tested envelope.

No generated artwork, source-alpha modification, audio retiming, release change or native Moho operation occurred. Source matte specks/fringes remain. `Motion-Review.json`, `Pilot.json`, `Arc-Pilot.json` and frozen local scripts retain the evidence.

Follow-up: CARTOON-EVAN-ARC-WRIST.md derives and checks the moved parent, adds independent wrist motion and records the remaining rejected attachment seam. Its next concrete work supersedes this initial study.
