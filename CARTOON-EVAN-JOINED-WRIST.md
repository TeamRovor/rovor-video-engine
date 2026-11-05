# Continuous right-wrist skin

The prior right wrist showed cut-edge fragments: the generated palm's wrist cross-section was narrower and offset relative to the original bare forearm, while the two pieces used different deformation fields. Feathering two mismatched silhouettes left a ragged join as the wrist turned.

`build_joined_wrist.py` registers existing source pixels locally. Alpha cross-sections sampled every quarter pixel fit the hidden-palm wrist's center/width to the original forearm. A seven-section smoothed fit releases back to the unchanged palm over 0–40 pixels along the wrist axis. Premultiplied source blending spans -36 to -12 pixels upstream. All original forearm pixels farther upstream and all registered palm pixels beyond the fit band remain exact. No new generated artwork, whole-character replacement or acoustic changes.

`JoinedWristArm` preserves the original forearm grid coordinates and extends the grid into the palm, using the same existing shoulder/elbow/wrist skin function. The wrist/palm now form one continuous skin surface with three hierarchical bone controls. The independent index remains its own source/mesh. Beyond wrist Y+30, skin uses the exact hand parent transform, matching the index attachment. The extra rectangular cells outside the transparent silhouette inverted during the first geometry check; the final mesh omits cells with no alpha support, including a three-pixel interpolation margin. A coverage check confirms that every nontransparent source pixel remains covered.

This is a genuine articulated local arm skin, not a flattened character sprite. It also means the right palm is no longer a separate runtime pixel layer. The source forearm and hidden-palm drawings remain separate versioned inputs. `JoinedWristSceneBody` uses the compact index and current material head; the rejected contact-art candidate stays excluded. `render_cartoon_scene.py --joined-wrist` and `export_cartoon_body_psd.py --joined-wrist` are opt-in. Previous scene/render modes and approved releases remain unchanged.

## Review

Outputs `../../outputs/evan-cartoon-joined-wrist` contain a full branded 0–10.1875-second scene and muted quarter-speed version, a native body-pixel before/after wrist review through 8.0–10.1875 seconds with the same recording/sample-clock waveform, final point/transition/rest frames, continuous source skin and a reopened seven-layer PSD. The PSD records runtime layers before the whole-body roll, not a native Moho bone project. Its seven layers are neck, torso, left hand, left arm, right index, continuous right arm/wrist/palm, and head. Mean premultiplied composite difference is 0.007254/255; export agreement is not a quality score.

Full-resolution source/assembled stills show the previously fragmented join closed at the inspected rest, transition and point poses. The new contour is more continuous; source inking/skin color still needs artist cleanup. The hand is still clenched, thumb/three neighboring digits share one drawing, and the compact resting index remains a construction study. Lips, F/V/L anatomy, shoulders, static legs and absent eye/blink acting remain unfinished. Continuous movie playback/listening approval is not claimed. This fixes a local surface/deformation mismatch; it does not establish professional animation quality.

All four final films decode without errors: full scene 489/1,956 frames (10.1875/40.75 s), wrist review 105/420 frames (2.1875/8.75 s), all at 48 fps.

23 targeted tests pass: skin-support mesh orientation through all 489 scene frames, preservation of the original grid/source pixels and distal palm, opaque wrist interior, full source-ink coverage, exact distal hand/index parent, plus compact-index and earlier scene/hand/socket regressions. Original word/phone annotations, articulation weights, recording and all 18 prior waveform/spectrogram flag reviews remain unchanged; exact phone timing is still unverified.

Only scratch `../cartoon-wrist/scene-final` and `review-final` represent final rendering. Earlier joined previews predate the source-exact distal copy and transparent-cell topology cleanup. Reproduce with the checkpoint's Python/dependency/recording paths. Scene is 489 frames at 48 fps; wrist close-up is frames 384–488 at 48 fps. The close-up assesses the wrist, not lip sync.

## Next work / limits

Design a softer neighboring-finger/palm pose and clean wrist/knuckle linework with an artist. Keep the shared wrist deformation rather than reintroducing independently cut contours. Improve the whole lower-mouth contour and designed contact-to-vowel shapes instead of further generated full-head variants. A human character artist/animator is still needed for anatomical and performance approval. The current CPU raster path limits iteration speed. The 720p study also uses a 512-pixel head and registered raster components; increasing output size cannot supply missing contours or anatomical drawings.

Main, V3/V4, approved symlinks/updater and native Moho projects are preserved. No merge, deployment or unattended Moho operation. The polished cartoon milestone remains incomplete; automation stays active.
