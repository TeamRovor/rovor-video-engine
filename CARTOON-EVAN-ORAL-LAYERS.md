# Separate cartoon oral layers

This revision replaces the experimental head's dissolved complete mouth textures with independently editable skin, cavity/outline, upper teeth, floor tongue, raised tongue, closed lips and F/V contact layers. The existing mesh renderer remains available as the baseline. Select --mouth-method layers in render_cartoon_head_study.py to use LayeredCartoonHead; the default remains mesh. Production V3/V4 rendering is unchanged.

## Source and build

Two built-in image_gen edits created a mouthless hidden skin plate and an empty oral cavity from the registered X and C drawings. Exact prompts are in cartoon-v1/oral-source/generation.txt; originals are preserved there. These sources register at upper-face ECC 0.99706 and 0.99695. Only the hidden regions are used, with cheek color matched to the original face; the original silhouette, sunglasses, hair and nose remain the source of the visible head. Generated plates do not replace the full visible head.

The original drawn C teeth, H tongue and X closed lip stroke are extracted as independent surfaces. There is one moving teeth texture rather than cross-fading tooth rows. A single raised tongue drawing scales/moves toward the floor for vowels and lifts for tongue gestures. Rounded O/U suppress the white teeth layer, and silent bilabial closure hides teeth/tongue. Separate F/V artwork is retained as an explicit candidate; it still needs refinement. The oral layers use 2x subpixel sampling before downsampling.

Interior surfaces are clipped behind the drawn lip boundary; the final comparison caught and corrected a tongue spilling outside the lower lip. A regression checks that a vowel tongue stays inside its cavity.

A source-level repair makes the hidden skin fully replace the old lip ink, with feathering outside the ink rather than through it. The first preview retained a faint smile corner; the final plate removes it. A regression checks the old lip region rather than accepting a passing geometry test as evidence of clean skin.

The tighter cartoon-only chroma key reduces magenta candidate pixels above alpha 32 from 1371 to 20 in C and 1447 to 70 in X. It preserves white teeth and black ink. Small residual edge specks remain; this is a reduction, not a claim of a perfect matte. The new registration lives in head-rig-v2 and preserves head-rig for comparison.

Rebuild: build_cartoon_heads.py (default output head-rig-v2), then build_cartoon_oral_layers.py. Source SHA-256 hashes and registration metadata are saved in oral-rig/manifest.json; source mutation is checked. The new hidden/segmented art is not approval-ready merely because it has layers.

## Review artifacts

Evan-Separate-Mouth-Layers.mp4 is a 231-frame, 4.8125-second 48-fps diagnostic using the unchanged real narration and acoustic plan. Evan-Mouth-Layers-Quarter-Speed.mp4 slows the closure/release region 4x, muted. Before-After.png compares native head renders at 0.583, 0.625 and 0.708 seconds against the earlier complete-texture blend. The doubled tooth rows at release are reduced by the single teeth surface. Closed lip strokes remain small and can still look rough at native detail; this is not finished studio acting.

Evan-Editable-Oral-Layers.psd contains seven real pixel layers, including hidden alternatives. Export/reopen verifies their names and produces an assembled PNG preview. It is an editable source assembly, not a native Moho project or a full-character rig. Runtime deformation is implemented separately.

69 tests pass, including closure/rounding visibility, exact upper-face stability, localized independent surfaces, matte semantics and the hidden-skin repair. These do not establish perceptual smoothness. Full-resolution still comparisons and rendered frames remain the basis for the visible findings.

## Limits and next steps

F/V still reads as a grimace and needs a genuinely designed lip-bite pose. L and dental gestures share a simplified raised-tongue control; they need an animator's review and distinct anatomy if they do not read correctly. The 18 acoustic timing disagreements remain unresolved. Some lip edges are rough because the original registered head is only about 409 pixels tall; simply upscaling will not create better line art. A vector/redrawn mouth construction or human animator may be needed.

The body, arms, hands, expressions and narration-driven acting are still unfinished. Next, build hidden-surface torso and arm plates and a real layered body rig, retaining these tests and artifacts for comparison. Do not keep polishing static heads indefinitely or call a floating-head diagnostic a finished entertaining cartoon. Main, V3/V4, updater/symlinks and Moho were untouched.
