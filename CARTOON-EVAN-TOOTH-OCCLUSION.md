# Rounded tooth occlusion study

The broad-mouth diagnostic identified the grey upper strip as the upper-teeth contribution. At source frame 148, existing rounded-tooth opacity factors multiplied to .53385 before sampled alpha and the cavity matte, leaving a translucent tooth band. This optional control study replaces those two rounded fades with geometric retraction behind the existing lip/interior mask. It uses the same separate tooth drawing, cavity/rim, tongue and character artwork.

## Construction and preserved baselines

OccludedTeethCartoonHead / --occluded-teeth extends BroadCavityCartoonHead. Current rounded art strength s (current E/F identity, with existing contact suppression) moves the sampled tooth target upward by `s * max(8, .45 * oralRingHeight)` native head pixels. The target translates before the existing 2x mesh sampling; no second bitmap translation/filtering is applied. Separate tooth pixels retain their colour and alpha until normal sampling and the existing lip/interior matte cover them. The rounded-art clip fade is bypassed and the final rounded-phone tooth factor becomes 1. Shared aperture and F/V material gates remain; this is not removal of all tooth transparency throughout the engine.

New default teeth-surface and rounded-visibility hooks preserve original source sampling/factors in older modes, including layered/material/lingual compositors. Three actual-time Broad baseline images (2.69,3.0833333333333335,4.6666667 s) remain pixel exact after hook extraction. Defaults and all earlier optional modes remain available. Cavity, tongue controls, jaw/face target geometry, recording, planner weights, word/phone annotations, brows and body acting are unchanged. No new artwork was generated or source pixel edited; prior source/PSD provenance remains intact.

The distance is an authored 2D relative-occlusion control, not measured jaw anatomy, rigid dental depth or new acoustic alignment. It is intentionally an optional study, not a native Moho rig.

## Actual visual review and limits

At source 3.0833 s, the broad translucent grey strip becomes a thin white edge at the upper lip. It is hidden at 3.1042 s as rounding continues. The preceding 3.0625 s pose retains its visible teeth. This is a more coherent local material treatment, but the two-frame disappearance must be judged in motion. Inspect normal/quarter-speed native-head comparison and branded integration through “little globe … your logo”/settle (source 2.5–5.0 s). Quarter speed repeats existing source frames; no new inbetweens are invented.

The source tooth band is still thin and can read mechanically. Shallow B/FV contact/release, distinct L/dental tongue poses, independent chin underseals, hand poses and eye/blink controls remain unfinished. The selected cartoon concept has simpler and more appealing expressions. A human character artist/animator is needed for final anatomy/performance approval; CPU raster warping and source pixels constrain iteration/detail. Do not claim studio quality from unit tests, boundary metrics or selected stills. Selected native-resolution frames are inspected; continuous playback/listening acceptance is not claimed.

Main, V3/V4, approved releases/symlinks/updater and native Moho projects are preserved. Moho was not launched/probed. This stays optional; the full polished cartoon milestone remains incomplete.

## Validation and scene-clock evidence

28 targeted checks pass: six new plus 22 prior head regressions. All nine pure X/A/B/C/D/E/F/G/H outputs remain exact versus BroadCavity. Actual partial-round changes remain within the mouth region with unchanged target geometry. The separate tongue and existing matte are preserved. Synthetic opaque input verifies that rounded identity no longer scales tooth material alpha; full E/F at energy .4/1 hide the teeth through masking instead.

Across all 489 scene-clock jaw/face targets the maximum difference is zero; the separate tooth target intentionally moves. The tooth audit samples 77 states with active rounding; 13 have rounded strength >=1−1e−9 and all have zero maximum tooth alpha after the matte. No contour fallback occurs. At frame 148 retraction is 4.5328 native pixels and the visible tooth material still has an alpha-255 core, versus the prior .53385 rounded opacity factor. At 149, retraction is 13.4187 pixels and residual alpha is only .0001314/255; at 150 it is zero. These numbers describe sampling/coverage, not anatomical correctness or lip-sync quality. Per-frame rows are saved in Tooth-Control-Audit.json.

All four final films decode cleanly: each normal file contains 120 frames / 2.5 s and each muted quarter-speed file 480 frames / 10 s at 48 fps. Selected native comparison frames 147/148/149/204/220/236 and branded frames 150/224/236 were inspected. Continuous playback/listening acceptance is not claimed.
