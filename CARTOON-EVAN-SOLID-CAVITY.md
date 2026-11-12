# Solid cavity through narrow vowel transitions

At 4.7917 s in logo, the old compositor dissolved an open cavity over skin while retaining the closed smile. This produced a muddy brown mouth patch. The aligned phone is OW; its late glide uses the engine F/UW target. The observed mixture is X=.5405/F=.4595, with no F/V contribution. Neither a recognition change nor a new mouth drawing was required to reproduce the fault.

## Change

New opt-in SolidCavityHead preserves cavity opacity once the inner slit opens, and retires the closed ink stroke over the very narrow opening interval. The cavity collapses around the drawn corner-to-corner tilt, rather than a horizontal axis. An initial opaque-only attempt exposed a second horizontal line and sparse ink near closure; the final tilt-preserving target and retained closed stroke address that regression. No source artwork, word/phone timing, recognition score or articulation weight changes.

LayeredCartoonHead now exposes oral_target, cavity_visibility and closed_visibility hooks with its original behavior preserved. Default renderer pixels match the prior implementation at three neutral/rounded mixtures. All nine pure poses, including contact poses, are exact between FVContactHead and SolidCavityHead. The changes affect intermediate oral pixels only. CartoonSolidMouthBody / render_cartoon_gesture_study.py --solid-mouth integrates the fix with the registered neck/collar, separate wrists and authored brows; older routes remain baselines.

## Actual review

Logo-Before-After.mp4 is a 1.5-second native-head comparison: source audio/time 3.75–5.25 s, 72 frames at 48 fps. Logo-Quarter-Speed.mp4 is muted, six seconds/288 frames. Both panels use identical timing and original narration. The waveform is drawn from original PCM16 samples on the source recording clock, with existing word annotations; it is not a synthetic amplitude estimate. Native-Blend-Sweep.jpg shows intermediate neutral/rounding blends without resizing the source crops. Body-Integration.jpg shows the final method in the existing branded scene. Only compare-final scratch frames match the final implementation; earlier compare/body scratch batches are superseded.

At the problem pixel (228,323), RGB changes from [162,90,59] to [79,15,14]: the material reads as a dark cavity rather than translucent skin. That is one regression measurement, not a quality rating. Full-resolution problem, weak-rounding and transition frames were inspected. The final weak-rounding sweep retains a dark connected lip line instead of the detached horizontal/ghost line seen in the first attempt. No continuous movie playback or listening verification is claimed.

Remaining limits: narrow lips are still visibly jagged; the topology produces a wedge-like early opening; the generic cavity and rounded lip construction need cleaner artist-designed contours. This does not establish smooth studio-level lip sync. It also does not correct F/V rolled-lip anatomy, L/tongue acting, pointing-hand linework/wrist joins, shoulder creases, static legs or missing eye/blink acting. A human character artist/animator remains needed for anatomical and performance approval. Existing 18 timing disagreements have visual waveform/spectrogram review, but exact phone boundaries remain unverified. Faster rendering hardware would speed iteration without fixing these drawing defects.

100 automated checks pass. Validation includes pure-pose preservation, changes confined to oral pixels, a rendered pigment regression, retained dark closure ink and non-inverting oral targets across pose pairs. Passing these checks does not establish perceptual animation quality. Source plan/audio hashes and the review clock are saved in Review-Evidence.json.

Next: review the narrow rounded contour and the relationship between lip rounding and rest/energy weighting using OW transitions, then carry the resulting components into a longer scene through favicon and its real pause. Design a relaxed-to-point hand transition with anticipation and held word accents; the current pointing drawing is still held throughout. Do not expand scope into more incidental motion before judging those transitions at normal speed.

Main, V3/V4, approved release/updater and native Moho files remain untouched. No merge/deployment or unattended Moho operation. The polished cartoon milestone is still incomplete; autonomous development remains active.
