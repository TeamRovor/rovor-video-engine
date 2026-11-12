# Cartoon head motion: first registered component

The cartoon source heads now register to a common 512x512 canvas using component bounds and constrained Euclidean upper-face alignment. The lowest upper-face ECC is 0.9865; that is a registration diagnostic, not an artistic quality score. Original source PNGs remain unchanged. Reproduce with build_cartoon_heads.py. Registered heads and a lower-face weight map are versioned in evan-character/cartoon-v1/head-rig.

cartoon_head.py maps actual drawn lower-face artwork through corresponding lip, cheek and jaw landmarks into one shared intermediate anatomy. A single neutral upper face is preserved exactly through row 291. The oral ring uses explicit annular topology with diagonals selected to remain positive across source poses; a generic Delaunay triangulation produced inversions near closed lips and was corrected. The open source artwork supplies oral pixels through an anatomical mask when closed-source lip texture would otherwise show through. No mouth is procedurally painted and this is not a sequence of flattened full-head swaps.

A 4.8125-second, 231-frame, 48-fps study uses the existing acoustic speech plan and reference recording. Normal-speed and muted quarter-speed films are exported in outputs/evan-cartoon-head-motion. The study presents the head at its native source detail with the word, sound, controls and waveform visible. It is intentionally a component diagnostic, not a completed explainer or an acting shot. Torso, arms, hands and expression controls are not assembled.

## Critical review

The closed-to-open still sequence is visibly cleaner after removing the closed-line overlay from open-mouth interiors. The 0.500/0.583/0.625/0.708-second native-resolution sequence shows the rounded vowel approaching closure, full sealed lips during the P interval at 0.60–0.65 s, then release. The upper face does not bounce with each sound.

Remaining defects are visible and must not be marked approved: narrow transitions near 0.583 s can retain extra lip strokes; teeth/tongue blends near 0.708 s look soft or doubled; the FV drawing around 0.3125 s still looks like a grimace rather than a convincing lower-lip contact. The drawn atlas also has small silhouette differences below the stable upper-face region. Separate teeth/tongue surfaces and better matched mouth contours are needed. A human animator/redrawn contacts may be required; more smoothing cannot solve ambiguous source anatomy.

62 tests pass, including every pose-pair interpolation at 21 samples, exact upper-face invariance and finite output. The minimum signed mesh area in pair testing is 0.28448 and over all 1059 reference control times is 0.29480. Positive triangles prevent foldovers; they do not establish smooth or appealing acting. The 18 acoustic word disagreements remain unresolved and must be reviewed independently.

## Next work

1. Separate and register oral interior, teeth and tongue layers, with matched contours; fix the documented narrow/FV artifacts before treating this component as accepted.
2. Build hidden-surface torso/head/arm/hand plates and a real body rig. Do not drop this head onto an unregistered body and call it finished.
3. Stage an expressive cartoon narration shot and review normal speed, slow speed and native-resolution frames.

Main, V3/V4, approved updater/symlinks and native Moho were untouched. No image generation was needed in this revision: source registration and native renderer implementation used the previously generated cartoon art.
