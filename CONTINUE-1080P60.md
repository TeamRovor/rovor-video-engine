# Continued existing Evan development — 2026-10-17

User requested continuation without repeating completed work, then 1080p at 60 fps.

This isolated checkout starts from the existing local body-rig commit `79bd397` on `development/evan-painted-rig`. The new local branch is `development/evan-timing-review`. The original checkout, main, approved release, V3/V4 and Moho remain unchanged. No merge, deployment or Moho launch occurred. Direct network git access is unavailable; the connected GitHub tools can preserve the changes on a separate development branch. See `ACTING-1080P60-CHECKPOINT.md` for the newer acting and vertical-format work.

Recovered regular-chat safeguards verbatim from `development/evan-art-rebuild` at `09e0717cb5608a14f481ebaa72df4c718168c24d`: character art gate, rejected procedural-render guard and its three dependencies, template and visual-reset documents. These are existing work, not new features. Existing local oral-layer/body-rig work is preserved alongside them. Do not replace the original source art with the rejected procedural drawing.

## New changes

- Body-study renderer defaults to 1920×1080 at 60 fps. Text and graphics rasterize directly at target size; artwork is independently resampled from the existing plates. This adds no missing source detail and does not resolve existing seams.
- Motion still uses seconds (`i / fps`); the 4.8125-second baseline becomes 289 output frames, preserving its duration to within one output frame. `--fps 48 --height 720 --end 231` retains the old study settings. This is still an opt-in study renderer, not a promoted production release.
- `render_profile.py` records landscape 1920×1080 and vertical 1080×1920 targets. Only the landscape body-study layout is implemented and verified here; vertical needs its own composition and must not be advertised as delivered.
- Moho converter CLI/default conversion now uses 60 fps; existing low-level exposure helpers retain their explicit legacy defaults. The new review sidecar distinguishes a short cue that is sampled from a cue receiving no frame. It does not retime cues or claim phoneme correctness.
- The original V3 `scene.json` contains 142 cues over 22.047375 seconds. At 24 fps, cue index 52 (7.71–7.75 s, B) is not sampled. Three other sub-frame cues are sampled. At 60 fps all 142 cues are sampled, and the timeline covers the audio using 1323 frames. This is sampling coverage, not validation of the 18 disputed word/phone anchors.

## Validation

22 focused output/timing/body-rig tests passed; 9 recovered art/guard tests passed. Sixty actual body-study frames rendered and encoded as H.264 yuv420p at 1920×1080/60fps. Decoder inspection verifies dimensions, frame rate, 60 decoded frames and 60 distinct frames. The one-second silent container check is internal validation, not a finished narration or artistic milestone. `git diff --check` passes.

## Artwork and next work

Original full-resolution design-sheet/setup/speech sources are readable in this checkout, resolving the regular chat's binary-access blocker. They remain reference sheets, not complete production plates. A new imagegen single-pose exploration used the exact original design sheet; it is NOT loaded into the rig, approved, or a layered deliverable. Inspect the generated halo/alpha and hand anatomy before considering any use.

Next: repair registered hidden shoulder/neck art, add genuine relaxed/pointing hand drawings and upper-face acting, review the 18 audio disagreements, and compose vertical framing separately. Keep 1080p60 output while improving the actual animation. Do not produce more rejected procedural demo films or treat tests as artistic approval.
