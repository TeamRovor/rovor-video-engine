# Rounded oral contour correspondence study

The previous rounded-art candidate dissolved two drawings whose ink boundaries did not coincide. During entry/release this left a doubled brown outline, even when the held rounded pose looked cleaner. This optional study moves both oral materials toward one common drawn silhouette before mixing their colour. It uses the existing source artwork; no new image generation, skin patch, flattened character or timing replacement.

## Construction

`ContourCartoonHead` extends the optional `RoundedArtCartoonHead`. The legacy candidate and all older defaults remain available. `--contour-art` integrates on the same layered body, gestures and official Rovor stage.

At each partial rounded-art state, the existing C-space oral material and registered E-space cavity/rim are sampled on the unchanged current oral mesh. Their alpha is upsampled 4x with linear interpolation, and the largest 50% contour is extracted. The centroid and 256 outermost radial intersections describe each drawn silhouette. The two profiles and centres interpolate with current rounded-phone art strength. Inverse radial fields sample both premultiplied materials onto that common boundary before colour mixing. Linear resampling preserves bounded coverage without new cubic lobes. The old/new interior masks follow the same fields, retaining separately controlled tongue/teeth behind the lip boundary.

The profile uses the outermost intersection at notches. This is a radial envelope approximation; it does not trace every concave ink feature, inner lip or anatomical landmark. It is not general retopology or evidence of anatomically correct speech. Raster boundaries still constrain precision. Degenerate profiles explicitly fall back to the previous candidate and count the event; audit records whether this occurs in the reference scene. Fully nonrounded and fully rounded states bypass the added resampling, preserving original endpoints exactly. Jaw targets, width controls, contact identity, recording, planner, word/phone annotations, brows and body controls are unchanged.

## Review and limitations

Review deliverables are in `../../outputs/evan-cartoon-contour`. The same-recording native-head before/after and full branded integration cover 2.5–5.0 s: “little globe … your logo” and settle. Normal-speed and muted quarter-speed versions retain the original source frames; quarter speed repeats frames rather than inventing inbetweens. Inspect native heads and the source concept sheet, not only thumbnails.

The contour pass targets the separated outer edge. It cannot fix the source's brown lip shading, thick lower lip, pinched shallow contacts, shared L/dental target, jaw/contact coupling, missing blink/eye rig, static legs or unfinished hand drawings. Relative to the selected concept, the mouth still reads heavier and less elegantly designed. A human character artist/animator is needed for final contour/anatomy/performance approval. CPU raster warping limits iteration speed; greater output resolution cannot supply missing artwork.

Keep this opt-in. The full polished animation milestone remains incomplete. Do not claim studio quality from silhouette disagreement counts, passing checks or selected stills. Native Moho was not launched/probed; main, V3/V4, approved symlinks/updater and native projects are preserved.

## Reference-clock audit

All 489 reference-clock geometry states remain exact. There are 67 partial rounded-art states; none falls back. Across these states the two materials’ unequal 50%-alpha silhouette pixels total 17,804 before correspondence and 822 after. Counts include repeated states and measure only silhouette agreement. The source design, phonetic interpretation and appeal are not scored by this metric. Reproduce with `audit_contour_art.py`; full per-frame rows are in Contour-Audit.json.

## Checks

63 affected checks pass: six new contour checks plus 57 existing head regressions. Pure X/A/B/C/D/E/F/G/H outputs remain exact versus the previous candidate; actual partial-rounding changes stay within the mouth region and tongue changes stay behind the aligned interior matte. A synthetic pair with known mismatched silhouettes verifies the fields reduce boundary disagreement; degenerate source profiles reject explicitly. These checks do not assess entertainment, anatomy or phonetic accuracy.

All four final films decode without errors: each normal file has 120 frames / 2.5 s and each muted quarter-speed file 480 frames / 10 s, at 48 fps. Selected full-resolution comparison frames 146/148/153/220/224/236 and branded frames 150/224/236 were inspected. Continuous playback/listening acceptance is not claimed.
