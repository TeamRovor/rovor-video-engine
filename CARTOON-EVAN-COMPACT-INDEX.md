# Compact index curl study

The narrated scene's resting index hangs as a long hook. `CompactIndexRig` adds an opt-in shallow curl with authored two-dimensional projected phalange lengths. `compact_controls` retains the existing word-anchored arm/wrist/head/body tracks and scales only index bend angles to 70%. At rest the angles are -7/42/24.5 degrees, and the projected segment length is 70% of the source drawing; at the full point, angles are zero and the original segment lengths/pixels are exact. `CompactCartoonSceneBody` uses the current material head; the rejected lip-art candidate remains excluded.

Each segment transform follows the preceding projected joint. Projection affects the segment's longitudinal direction while keeping its local transverse width; it is an authored cartoon construction, not measured 3D depth or physical bone shortening. Broad existing skin weights still blend the segments. It reuses the original index and hidden-palm surfaces: no new generated art, pose-sprite crossfade, source replacement or timing change.

The first trial combined aggressive shortening with the old deep curl, causing mesh inversion and an actual hole at the crease. That trial was rejected. Rotating the root inward also exposed a cut edge behind the thumb and was rejected. The final shallow range preserves orientation through all 489 source-scene frames (minimum signed-area ratio 0.10794). This geometric check prevents the observed foldover; it does not prove good hand anatomy or acting.

## Review and limits

Outputs `../../outputs/evan-cartoon-compact-hand` contain a native body-pixel before/after right-arm comparison from 8.0–10.1875 seconds, its muted quarter-speed version, original sample-clock waveform, native source-resolution current/compact rest and point drawings, and branded full-scene point/transition/rest stills. The close-up intentionally assesses the hand rather than lip sync. The full scene is available through `render_cartoon_scene.py --compact-index`; previous modes/defaults remain unchanged.

Full-resolution native hand, body-pixel close-up and branded stills were inspected. The new rest has a smaller/shallower hook and retains the same full pointing silhouette. It is still a stylized clenched-hand construction rather than a designed naturally relaxed hand. The thumb and three neighboring fingers remain one drawing. The wrist edge is visibly rough; source crease placement and limited hand volume still require artist cleanup. Continuous movie playback/listening acceptance is not claimed. Do not equate the smaller hook, passed geometry checks or decoded films with studio quality.

Both final films decode without errors: 105 frames/2.1875 s normal and 420 frames/8.75 s quarter-speed at 48 fps.

17 targeted checks pass, covering all-frame orientation, shared projected joints, exact full-point pixels, unchanged other acting controls, rejected unreviewed angles, and existing scene/hand/socket regressions. Source art, narration, acoustic word/phone annotations and planner weights are unchanged. All 18 anchor flags retain prior waveform/spectrogram visual review and exact-phone uncertainty.

## Next work

A designed softer palm/neighbor-finger pose and clean wrist/knuckle construction are still needed; a character artist/animator remains necessary for final anatomical/performance approval. Do not continue solving missing folded creases by forcing deeper bends into straight source art. Mouth contours and F/V/L anatomy also remain unfinished; the last lip-art trial was not promoted. CPU raster rendering limits iteration speed, not the missing drawing decisions.

The compact mode is an optional development study. Main, V3/V4, approved symlinks/updater and native Moho projects remain untouched. No merge, deployment or unattended Moho operation. The polished milestone remains incomplete; automation stays active.
