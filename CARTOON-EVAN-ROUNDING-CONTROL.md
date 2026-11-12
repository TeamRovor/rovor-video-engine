# Phone-driven rounding with independent jaw opening

Quiet vowels were blended toward the wide resting smile, changing lip width along with jaw opening. This opt-in mode derives rounded lip width from the existing acoustic phone gestures before energy attenuation. Audio energy still drives the original jaw/opening target. It reuses the current registered cartoon layers; no artwork or recognition data was generated or replaced.

## Control change

`acoustic_weights(..., energy_weighting=False)` exposes the existing phone/coarticulation distribution while retaining consonant contacts and the explicit silence gate. The default remains True. All 1,059 default weight vectors are bit-identical to the previous version. `RoundedCartoonHead` uses the share of active E/F rounded targets to blend only mouth X coordinates toward this shape distribution. Every Y coordinate and every non-mouth anchor remains identical to the energy-weighted target. Current bilabial/FV contacts suppress anticipatory rounding.

The first unfiltered implementation held the pucker but released it too sharply. The final shape-only control uses a symmetric triangular seven-sample window spanning ±62.5 ms. This is an authored lead/release for animation, not a newly measured phonetic boundary. Original word/phone annotations, audio, cached controls and jaw timing remain unchanged. On the logo release region, the initial unfiltered new control peaked at 29.96 source pixels/frame; the final version peaks at 11.95, comparable to the prior method's 11.98. This does not establish perceptual smoothness.

Full-head inspection then exposed an unwanted cheek mark caused by narrowing the skin mesh along with the lips. The final `skin_target` retains the original energy-weighted face/jaw deformation; only the separate oral surfaces receive the lip-width change. A rendered regression protects cheek/skin pixels outside the mouth. The selected cartoon identity is preserved.

`CartoonRoundedBody` and `render_cartoon_gesture_study.py --rounding` integrate the mode with the existing registered neck/collar, separate wrists and authored brows. Earlier classes/defaults remain baselines. The explicit shape_weights path passes through layered skin/oral and expressive-brow rendering; no shared mutable per-frame head context was introduced.

## Review

The normal before/after is 72 native-head frames at 48 fps (source 3.75–5.25 s), with the original narration and PCM sample-clock waveform. The muted quarter-speed version is six seconds/288 frames. `render_solid_mouth_review.py --rounding` reproduces it. Native-OW-Comparison.jpg shows source-pixel crops through both OW vowels in logo. Body-Integration.jpg uses the official Rovor mark and current body rig. Width-and-Jaw-Review.png and Control-Review.json record the width change and unchanged jaw targets across the recording. Shaded OW regions use existing alignment annotations; exact boundaries remain unverified.

The inspected quiet tail now retains a narrower pucker rather than widening toward the rest smile while still speaking. The cavity is still wedge-like and its outline remains jagged. Source art and the generic cavity topology still need artist-designed rounded lips, lower-lip roll and clean contours. Full-resolution head/crop and sampled transition frames were inspected; no continuous movie playback or listening verification is claimed. This is a control separation and release improvement, not studio-ready lip sync.

108 automated checks pass. Validation covers gain-independent rounded width, energy-dependent opening, full-contact protection, silence settling, immutable plan data, reduced new-control release steps, non-inverting target/oral meshes and a rendered cheek-mark regression. All 1,059 reference frames retain exact jaw/non-mouth coordinates and default weights. These checks do not establish drawing quality or alignment accuracy. The 18 prior timing disagreements have waveform/spectrogram visual evidence review; exact phones remain unverified.

## Next bounded work

Carry this control into a longer narrated scene through favicon and its pause, with a designed relaxed-to-point hand transition and readable held word accents. Stop treating isolated mouth sweeps as a finished animation milestone. Redrawn rounded/FV/L anatomy and cleaner hand/wrist/shoulder construction still require artist/animator review. Legs remain static and eyes have no blink rig behind the glasses. CPU rendering affects iteration speed; faster hardware cannot replace missing drawings.

Main, V3/V4, approved releases/updater and native Moho files are preserved. No merge, deployment or unattended Moho launch/probe. The full polished cartoon milestone remains incomplete; automation stays active.
