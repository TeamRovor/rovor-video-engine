# Broad oral cavity/rim artwork study

The existing broad cavity source contains a painted red floor as well as the separate animated tongue. This optional study removes that painted floor and redraws the mouth-only contour. It does not replace surrounding face paint, teeth, contact drawings or the character with a flattened image.

## Source, working parts and runtime

Built-in imagegen edited the original isolated broad cavity. Before supplying the reference, only hidden RGB where alpha equals zero was cleared; visible source pixels and alpha were unchanged. The edit preserves a broad three-quarter smile, with a thin ink contour and no painted floor shape. It retains cavity gradients despite the prompt asking for a single flat fill. Source, reference and exact prompt are saved in broad-source-v1. Chosen broad-mouth-v1.png SHA256: 85e71f85065c5e86b3f41a2b667732851d348c33111c41a6b5ee61df073b5da9.

build_broad_oral_art.py registers separate cavity/rim and an interior occlusion matte in broad-rig-v1. Source alpha bounds [180,509,1085,907] fit the previous visible C bounds [195,316,281,361]. This is an authored affine fit to canonical C controls, not traced anatomical correspondence. Near-solid alpha >=250 is normalized, with 12-source-pixel cavity underlap and 4x sampling. Manifest records source/reference/prompt hashes, generation chain, matrix and limits; animationReady=false. Registered source pixels rebuild exactly.

BroadCavityCartoonHead / --broad-cavity extends the optional lighter-rounded-mouth rig. New broad cavity and rim warp independently in C space before alpha-over; the interior matte clips separate teeth/tongue. Partial rounding retains existing radial contour correspondence with the lighter O source. Two new default-pass-through broad-surface/matte hooks allow existing modes to retain their original source and pixels. Three actual-time existing LightLip images (2.69,3.125,4.6666667 s) remain pixel exact after hook extraction. Geometry, acoustic weights, recording, word/phone annotations, eyebrows and body controls are unchanged.

A two-layer editable source-space PSD contains real cavity/rim pixel layers. It is a construction plate, not a complete character or native Moho rig. Runtime mesh, teeth/tongue and timing remain separate.

## Critical review and limits

Initial native views show a cleaner broad contour and remove the old painted red floor. The grey upper strip remains: the old upper-teeth surface also contributes to that appearance. Do not claim the cavity edit solves the entire brown/grey band. Teeth registration/design, shallow B/FV contact and release still need work. Generated gradients, affine source proportions and inner-lip correspondence remain limitations. The selected concept's simpler mouth design remains the reference.

Review same-audio native-head before/after and branded integration, source 2.5–5.0 s through “little globe … your logo”/settle. Normal and muted quarter-speed comparisons use identical source timing; quarter speed repeats source frames. Inspect selected native-resolution frames and the concept sheet; continuous playback/listening acceptance is not claimed. This is an optional development source study, not a polished/studio-quality performance or verified phonetic accuracy.

A human character artist/animator is needed for final anatomy/performance approval. CPU raster warping and native source pixels limit iteration/detail; increased resolution cannot invent missing drawings. Main, V3/V4, approved releases/symlinks/updater and native Moho projects are preserved. Moho was not launched/probed. Full animation milestone remains incomplete.

## Validation and layer diagnosis

22 targeted checks pass (five new plus 17 prior head checks). Closure/FV/full-rounded pure controls X/A/G/E/F remain exact versus LightLip; broad changes stay within the mouth region with unchanged target geometry. Separate tongue changes remain behind the new matte. All 489 scene-clock geometry states remain exact; 67 partial rounded states have zero fallback. Unequal 50%-alpha silhouette pixels between broad/rounded materials total 19,071 before correspondence and 644 afterward. These repeated-state counts measure alignment only.

At source frame 148 (3.0833 s), a diagnostic removes only the upper-teeth contribution after existing clipping. The grey upper strip disappears, identifying that layer as a contributor. The diagnostic does not distinguish source design, geometry placement, matte coverage or cumulative opacity as the remaining root cause. Inherited tooth rendering includes multiple rounded-phone opacity factors; inspect those alongside lip occlusion before a redraw. The right-hand tooth-free panel is explicitly NOT a proposed design. Reproduce with render_broad_teeth_diagnostic.py; image is Upper-Teeth-Diagnostic.jpg.

At the diagnostic frame, the rounded-art tooth factor is .6820 and the later rounded-phone composite factor .7827; with other control factors at 1, their product is .53385 before sampled pixel alpha and the interior matte. This explicitly documents partial tooth transparency as a rendering contributor to investigate, not measured anatomical occlusion. The complete weights/factors are saved in Review-Evidence.json.

All four final films decode cleanly: normal 120 frames / 2.5 s, muted quarter speed 480 frames / 10 s, at 48 fps. Selected native comparison frames 134/148/153/220/224/236 and branded frames 150/224/236 were inspected. Continuous playback/listening acceptance is not claimed.
