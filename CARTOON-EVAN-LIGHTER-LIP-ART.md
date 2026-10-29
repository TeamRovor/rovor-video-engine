# Lighter rounded oral artwork study

The selected cartoon concept has a simple inked O mouth. The previous working source introduced a fleshy peach lower-lip band and baked red floor, which competed with the separate animated tongue. This optional study edits that isolated source component toward the concept's simpler construction. It does not replace the head or character with a flattened image.

## Actual source and registration

Built-in imagegen edited the previous rounded source with `source/design-sheet-v1.png` as style context. The first result removed the peach band and red floor but retained cavity gradients. A targeted follow-up requested one flat burgundy interior; it did **not** fully remove the gradients. The saved source remains generated pixels, not a falsely described flat fill. Both actual outputs and exact prompts are in `light-lip-source-v1`; selected source is `light-mouth-v2.png`, SHA256 `d2b759ad9cc454d087a13c289d4bde1fe68753fb0252099fa4bbc4e9c8510e50`.

`build_light_lip_art.py` extracts the burgundy fill, supplies a 12-source-pixel underlap and separates cavity/rim plus an interior occlusion matte. It normalizes intended-solid alpha >=250, fits alpha bounds [491,445,802,845] into the existing canonical E-space [211,320,240,366] and samples at 4x before returning to native 512. This authored affine fit is not anatomical registration. Source/reference/prompt hashes, generation chain, matrix and limitations are recorded in `light-lip-rig-v1/manifest.json`; animationReady remains false. Registered pixels rebuild exactly.

`LightLipCartoonHead` uses those separate working components on the existing contour/tongue rig. `--light-lip` integrates on the current articulated body/official Rovor stage. Current phone identity, rounding correspondence, geometry easing, teeth gating, separate tongue and occlusion are inherited. Nonrounded controls, old artwork modes, defaults, recording, planner and timing annotations remain unchanged.

The two-layer source-space PSD contains editable cavity/rim pixel layers. It reopens with mean premultiplied difference .0003315/255. This is a construction plate, not a complete character rig or native Moho project.

## Critical comparison

The initial native held-vowel comparison loses the peach lower edge and duplicated red floor; the tongue remains separately visible. The opening looks cleaner and closer to the selected concept, though tongue detail and cavity shading are still heavier than the concept's small O. Entry still inherits a brown strip from the older broad C-mouth drawing. This pass does not solve that source, pinched B/FV contacts, distinct L/dental tongue poses, independent chin underseals, missing eye/blink controls or hand anatomy.

Review normal/quarter-speed native-head comparison and full branded integration in `../../outputs/evan-cartoon-light-lip`, source 2.5–5.0 seconds through “little globe … your logo”/settle. Quarter speed repeats source frames rather than creating inbetweens. Selected native-resolution frames are compared against the original concept; continuous playback/listening acceptance is not claimed.

Keep this optional, not promoted into defaults. A human character artist/animator is needed for final anatomy/performance approval. CPU raster warping constrains iteration speed and source pixels constrain detail; higher output resolution cannot supply the missing drawings. This is not polished/studio-ready animation. Main, V3/V4, approved symlinks/updater and native Moho projects remain preserved; Moho was not launched or probed. The full milestone remains incomplete.

## Validation and correspondence audit

17 targeted checks pass (five new plus twelve existing contour/rounded-art checks). Nonrounded X/A/B/C/D/G/H controls remain exact; new rounded-art changes stay within the mouth region and the independently moving tongue stays behind the interior matte. Registered cavity/rim cover the reference's opaque core. These are component/regression checks, not perceptual lip-sync or artistic acceptance.

Across all 489 scene-clock states, geometry remains exact versus the previous contour-art candidate. All 67 partial rounded states register without fallback. Unequal 50%-alpha silhouette pixels between the old broad material and lighter round material total 20,296 before radial correspondence and 813 afterward. This counts repeated states and measures only outer-boundary alignment. It does not show inner-lip correspondence, speaker anatomy or verified phoneme boundaries. Reproduce with `audit_contour_art.py --light-lip`; per-frame rows are in Contour-Audit.json.

All four final films decode without errors. Each normal file contains 120 frames / 2.5 s; each muted quarter-speed file 480 frames / 10 s, all at 48 fps. Final native comparison frames 148/150/153/224/236 and branded frames 150/224/236 were inspected. No continuous playback/listening acceptance is claimed.
