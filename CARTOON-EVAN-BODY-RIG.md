# First cartoon body rig study

This opt-in study connects the separate oral-surface head to original setup artwork, with independent left/right shoulder, elbow and wrist transforms. It does not alter V3/V4 or the default renderer. `cartoon_body.py` uses hierarchical joint transforms, continuous elbow/wrist skin weights and premultiplied-alpha arm sampling. Authored motion includes delayed forearm/wrist follow-through, modest head tilt and torso roll. The camera deliberately crops the static legs below the knees.

## Artwork and rejected candidate

The original cartoon setup supplies the torso and both arms. Polygon masks retain a short original upper-sleeve overlap beneath each animated arm. These are registered working components, but they are not newly drawn, complete hidden surfaces. The built-in imagegen attempt in `body-source/torso-hidden-v1.png` moved the shirt/neck and failed the registration gate; it is retained with its prompt and is NEVER loaded by CartoonBody. `body-rig/manifest.json` records this rejection, hashes, joint coordinates and `animationReady=false`.

A four-pixel-layer PSD exports actual torso, left arm, right arm and head surfaces at rest. It is reopened and its premultiplied composite compared with runtime assembly (mean difference 0.00385 / 255). The separate seven-layer oral PSD remains the facial source. The body PSD contains pixel artwork, not executable bones or a verified Moho rig; joint metadata and deformation code are separate.

## Review shot

`render_cartoon_body_study.py` renders 231 genuinely different 48fps frames (4.8125 seconds), using the existing script/acoustic speech plan and original narration. The graphic shows the browser globe discussed in the first sentence and the official Rovor mark. A quarter-speed silent version permits closer movement review. Review files live in the chat's outputs/evan-cartoon-body-rig directory. Full-size rest/gesture comparison and stage frames accompany the films.

Visual inspection found and removed the original chin fragment under the moving replacement head, and expanded the arm mattes to recover clipped shoulder contours. Inspection at native component resolution still shows extra/doubled folds at the armpits under the broad gesture, an imperfect neck/collar transition, slight matte/edge roughness and deformation of a single hand drawing. The upper face is still held, with no brow/blink expression rig. Both hands are one open pose, fingers are not articulated, legs are static and no torso perspective turn exists. Mouth F/V remains a grimace candidate. These limits prevent a production-quality claim.

The local renderer uses CPU raster meshes and supersampled mouth surfaces; full-resolution source art is about 409 pixels tall for a head and roughly 100 pixels across each hand. More pixels at export cannot create missing detail. Rendering speed is an iteration cost, not the main reason for the visible anatomy defects. Clean hidden shoulder/neck surfaces, alternative hand poses, F/V cleanup and acting review by a character artist/animator remain necessary. No native Moho launch/probe was attempted.

72 checks pass, including continuous joint attachment, independent controls and non-inverting arm triangles throughout the authored shot. These safeguard implementation only. The 18 acoustic word-anchor disagreements remain open and have not been verified by this body-rig pass.

## Reproduce

Use the existing local Python/dependencies described in the checkpoint. Build with `build_cartoon_body.py`; render with `render_cartoon_body_study.py PLAN FRAMES`; export with `export_cartoon_body_psd.py PLAN OUTPUT.psd`. None is enabled in an approved release.

Next: replace the exposed armpit/neck seams with artist-faithful registered hidden surfaces; add genuinely different relaxed/pointing hand drawings; then inspect flagged speech intervals against waveform/spectrogram evidence before increasing gesture range or calling the acting polished.
