# Evan cartoon arc and independent wrist

`ElbowArcReview.hand_parent(angles)` now provides the rigid source-to-posed hand transform for the finite-radius elbow construction. It has no body-canvas padding; `ThumbsUpPlane.pose` supplies the existing 220px padding. The transform agrees with actual distal mesh vertices, including an independently controlled wrist. Current speaking scenes still do not import this review class.

The parent translation comes from the arc-mapped wrist, with the shoulder and elbow rotations applied in hierarchy. Wrist rotation remains about the source wrist before that parent. At shoulder−5°/elbow−135°, the new anchor differs from the old hinge FK by 88.33655066035035 native pixels. Reusing the old FK matrix would visibly detach a registered hand.

Wrist skin follows the existing 60px axial smooth influence, transformed through the rigid forearm beyond the elbow arc. The validated review envelope is shoulder−5..0°, elbow−135..0°, wrist−15..15°. Upper/cuff material proximal to the wrist influence stays exact as the wrist changes. This is independent wrist motion of the existing open-hand drawing, not independent finger articulation or a new hand pose.

## Checks and rendered material

Four arc tests and the five existing hand-plane tests pass. The arc checks sample 1,224 combinations (three shoulder angles, 136 elbow angles and three wrist angles). All retained triangles stay positive; minimum area2 is 140.47442335903804 in that probe. Maximum distal-parent coordinate error is 0.00000768358177083428px. Tests also check proper rigid matrices, fixed moved wrist anchors during wrist rotation, unchanged proximal material, source preservation, invalid inputs and exact neutral composition on the padded canvas.

Local output: `outputs/evan-cartoon-arc-wrist/` from the workspace root. `Normal.mp4`/`Slow.mp4` compare fixed wrist with the moving wrist on actual native arm material; `Stage-Normal.mp4`/`Stage-Slow.mp4` show the candidate on the existing official Rovor stage. Normal:96frames at48fps; muted quarter-speed:384frames. All four fully decode. The elbow is held at−135° and the wrist eases through0/+15/−15/0. No narration synchronization, speech-plan change or audio retiming is included.

All96native wrist/hand crops in six sheets and native whole-arm/full-stage extrema were inspected. The existing palm remains connected during this small wrist arc. Its contour is still noisy, the cuff keeps its pointed inner notch/compressed shading, and the held face/body plus fixed fingers read as a construction exercise. Anatomical and polished animation acceptance remain false. Positive geometry is only a structural check.

## Held thumbs-up attachment remains rejected

Six held attachment pilots use the corrected parent at wrist−15/0/+15 and transverse centers0/−6.75px. The old hand is excluded by an axial runtime ownership mask on a working copy of the existing arm; raw source files/alpha are unchanged. The new hand is placed behind that retained arm material. Both center choices still expose a diagonal wrist-stub cut, protruding edge and mismatched contour. All six are rejected, including the best centered wrist-zero image. These are registration pilots, not working production hand replacements.

The thumbs-up source retains its earlier unapproved matte/fringes. Its registration file, source PNG and the current speaking scene are unchanged. No new artwork was generated in this study. Original pilot scripts and JSON evidence are frozen locally.

Next: fit two transverse source/target guides for the wrist stub and give the two components an explicit hidden ownership overlap. Start with the held raised wrist-zero pose, then test±15°; reject exposed cuts rather than hiding them with a broad dissolve. Keep the finger silhouette rigid during that attachment fit. Do not expose thumbs-up throughout the low-arm lift, where it reads thumbs-down. No speaking-scene integration until the seam and cuff silhouette pass visual review.
