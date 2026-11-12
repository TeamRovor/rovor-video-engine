# Anchored face skin under independent mouth layers

Rounded vowels pulled a gray/brown fragment of sideburn/ear ink onto Evan's cheek. The skin deformation still followed the narrowed oral landmark ring, even though the cavity, teeth, tongue and lips already had their own meshes. This opt-in pass keeps the skin ring at the original neutral source coordinates and preserves the articulated external skin anchors, including the jaw/chin. It removes the inspected smear without freezing the lower jaw or changing speech timing.

AnchoredCartoonHead extends SeparatedCartoonHead and overrides only skin_target. The first 32 skin anchors stay at POINTS['X']; anchors 32 onward retain the previous jaw target. Oral targets, tongue lift, material weights, contact geometry, rounding lead/release, audio-driven geometry easing and brows retain their previous controls. AnchoredCartoonSceneBody / --anchored-skin puts the head on the same continuous-wrist/independent-index cartoon body. Older modes remain unchanged for comparison. No generated art, bitmap patch, facial crop replacement or native Moho edit was used.

## Evidence

Across all 489 existing scene-clock samples, maximum oral-target and external-jaw-anchor differences are both zero. The new skin mesh retains positive orientation (minimum signed doubled triangle area .9903469). In the native cheek region x296:333/y294:320 at source 3.125 and 4.6667 seconds, mean RGB difference from original cheek paint falls from 9.1234/10.6951 to exactly zero. These measurements establish a local regression fix, not artistic quality.

29 affected checks pass: five new anchored-skin checks plus 24 existing separated-jaw, tongue, material and rounding checks. They protect original sideburn pixels in E/F, exact rest pixels, unchanged opaque oral cores, moving jaw anchors and non-inverting skin meshes. A first test incorrectly treated cubic alpha values above 255 as fully opaque; inspection showed one-level fringe differences. The corrected check requires exact alpha=255 cores and bounds the tested overshoot fringe to one 8-bit level. The legacy resampler still needs premultiplied-alpha range enforcement before compositing; this pass does not conceal that separate defect.

Review outputs ../../outputs/evan-cartoon-anchored-skin. Same-audio native-head before/after and full-frame branded integration shot both cover recording time 2.5–5.0 seconds, including “little globe … your logo” and the following pause. Each normal film has 120 frames at 48 fps; each muted quarter-speed version has 480 frames and repeats source frames rather than inventing in-betweens. All four completed films decode cleanly at 48 fps. Skin-Anchor-Contract.json records native source-space anchors, not a new image or native Moho project.

The selected cel-cartoon direction is retained. Native 512-pixel head pairs at rounded vowels show the original clean cheek/sideburn contour instead of the stray ink triangle. Tongue-contact and F/V samples retain their mouth construction. Jaw/chin acting remains articulated. Mouth shape design is still rough: rounded vowels look mechanically warped, narrow lips pinch, the tongue compresses in shallow apertures, and L/TH/DH still share one target. The anchored skin is deliberately stable under visemes; separately authored cheek acting can be added later. Continuous playback/listening acceptance is not claimed.

No alignment annotation changed. All 18 flagged word regions retain their waveform/spectrogram visual review and unverified exact boundaries. The before/after uses identical source audio, mouth controls and sample-clock waveform; the cheek fix provides no new evidence of phonetic timing accuracy.

## Next work / limits

Bound premultiplied cubic-sampling values before oral compositing, using explicit edge/closure evidence and existing endpoints as baselines. Then redraw/design clean shallow-contact and rounded-vowel contours and separate L/dental tongue construction. Consider independent jaw/chin movement under lip seals. A human character artist/animator is still needed for final anatomy and performance approval. Hand rest/neighboring fingers, shoulder linework, static legs and missing eye/blink rig remain unfinished. Native raster source detail and CPU rendering limit iteration; more output resolution cannot provide missing drawings.

Main, V3/V4, approved releases/updater and native projects are preserved. Development commits only, no merge/deployment or unattended Moho action. Full polished cartoon milestone remains incomplete; heartbeat stays active.
