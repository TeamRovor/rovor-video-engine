# Rovor painting film — October 18 V10 motion audit and rejected gesture studies

**This is a quality/reusability pass, not a new V10 approved movie.** Current film remains **V9B**: 9,377 decoded 60-fps frames, 156.28333 seconds (2:36.28), with 106.404 seconds of the original 262.687313-second audio still without rough coverage. Do not imply any more time has been rendered or the film is artistically approved.

## Actual new work

- Audited the **real V9B 2:36 landscape and portrait MP4s** with FFmpeg grayscale decoded frames at 2 FPS (313 samples/312 adjacent half-second comparisons per orientation), 5-second windows. Never used the storyboard or manifest as a substitute for decoded video.
- Built portable `visual_motion_audit.py` and automated tests. Audits exact 60fps input and dimensions, computes changed-pixel fraction, identifies probable low-motion windows, and explicitly refuses to certify creative quality. The original movie was read-only.
- **15** low-motion windows in landscape and **13** in portrait, of which **13** coincide across both. Threshold: median changed area <0.8% at 10/255 gray-level difference, and at least 60% of sampled comparisons are nearly still (<1.2% changed area). A low-motion window is an **investigation flag**, not proof of a defect: character listening and intentional holds may be valid, and hard cuts can hide weak acting.
- Inspected actual decoded frame grabs at 25, 35, 86, 91, 110, 112, 114, 149, 151, 155 seconds. The 110 and 112-second frames are visually unchanged, corroborating the frozen furniture-protection blocking. Early graphical estimate/photo sections need a cartoon rewrite instead of minor motion tweaks.
- Authored two **unapproved experiments**: (1) customer hand/cuff geometry derived from the actual scene's shoulder/elbow/wrist and temporal action track instead of an offscreen pointing arm in the V9B mechanic scene; (2) cloth corner tuck and painter arm recovery at source 110–114 seconds to avoid the frozen protected-couch pose. These pass structural/raster-change regression tests but still look geometrically awkward. Neither was edited into any reviewed video, and there is **no approved V10 render**. Prior V9B videos and original art are unchanged.
- Regression results: 34 passing source and audit tests in the mechanic/motion modules, plus 4 passing scene tests for the cloth candidate. They do **not** establish artistic quality, English word alignment, final audio mixing, or release readiness.

## Visual-rebuild queue, directed by actual evidence

| Priority | Source time | Evidence | Production redesign requirement |
|---|---|---|---|
| 1 | 1:50–1:54 (110–114s) | Painter/furniture image freezes across 110 and 112 seconds; median changed pixel fraction in 110–115s window 0 | Redraw physically believable cloth grip, fold and tucked fabric; contact through hand/couch; expressive weight shift; visual transition to repair close-up. Existing experiment only proves motion, not good art. |
| 2 | 0:25–0:40 | Two photos/estimates shown as flat interface panels and held almost still; both formats flag 25–30 and 35–40 | Physically staged customer discovering hidden scope differences, believable paper handling and shot/reaction coverage instead of static text cards. |
| 3 | 1:25–1:35 | Flat blue room and browser interface with minimal movement; low-motion in both 85–90 and 90–95 | Make digital gallery a physical interaction: actual project thumbnails reveal process behind finished photos; meaningful visual cause and effect. |
| 4 | 0:45–1:20 | Several low-motion stretches in both orientations | Revisit pacing and blocking; expressive hand/object acting, meaningful camera movement and clearer transitions. Use narrator word landmarks after genuine listening. |
| 5 | 2:24.8–2:36.28 | Mechanic estimate is an improved story scene but arms/faces remain simple; last 155–156.28 window nearly still | Rebuild grasping and reaction poses with registered art, then animate/caliper contact with native surface detail; do not promote the geometry-only V10 study. |

**Broad artistic direction:** cartoon filmmaking, not slides with moving titles. The existing painter is a *hypothetical educational character*, never a claimed Rovor customer; exact Evan original dark hair/sunglasses/navy shirt/black tie rig remains preserved. Do not replace source art with a lookalike.

## Repeatable audit

`python visual_motion_audit.py /path/to/film_landscape.mp4 --out motion-landscape.json`

`python visual_motion_audit.py /path/to/film_portrait.mp4 --portrait --out motion-portrait.json`

Required: Python 3, NumPy, FFmpeg and FFprobe. Tests: `python -m unittest -v test_visual_motion_audit`.

## Source integrity and release status

- Original ElevenLabs source audio SHA256: `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`.
- Original MP3 is private and excluded from all new code bundles and GitHub.
- Prior video SHA256s, render source, and draft PR #5 are preserved. **main not modified; do not merge or publish.**
- Full narration is not transcribed/word-verified; closing Rovor pronunciation and URL need actual listening and a user-approved corrected voice if wrong.
- Artistic approval remains false. **The priority is rebuilding the weak footage while continuing to improve reusable animation/rig QA.**