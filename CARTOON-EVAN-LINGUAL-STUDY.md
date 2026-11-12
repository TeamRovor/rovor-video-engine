# Rooted tongue construction study

The previous raised tongue was a large round shape that slid toward the mouth floor between contacts and could cover upper incisors. The opt-in LingualCartoonHead replaces it with a smaller generated blade attached to a separate original tongue-floor layer. Upper teeth are now composited in front. Hair, glasses, brows, face silhouette, lip/jaw targets and acoustic annotations retain the existing construction.

This is an entertaining cel-cartoon study, not a realistic portrait, calibrated vocal-tract model, accepted animation or a native Moho project. `tongue-rig/manifest.json` deliberately keeps animationReady false.

## Source and registration

The imagegen skill produced one transparent isolated blade, using the cleaned old isolated tongue as an edit input and head-rig-v2/head-H.png only as style/context. Exact prompt and isolated reference are versioned in tongue-source, alongside the raw generated blade-v1.png. A first thin-blade-only assembly looked like a hanging uvula and was rejected. The current assembly adds the original broad tongue floor to make the blade visibly rooted.

build_tongue_blade.py uniformly registers the generated alpha bounds [549,505,755,769] to a 32-pixel-high blade in the native 512-pixel head, top 322, fixed source-space root [237,354]. The original floor is registered C→H separately. Source hashes, context hash and affine matrix are recorded. These registered parts are working components, not claims that a generated source plate is itself an animation rig.

At runtime the blade compresses toward its fixed root (vertical scale .42→1, horizontal .8→1), then both floor and blade follow the existing oral mesh and cavity mask. The floor does not slide with the blade. The existing tongue-viseme weight H supplies lift; no new predictor, retiming, energy correction or allophone classifier was added. H also serves L, TH and DH in the current catalog, so the clear-L-inspired drawing does not resolve their distinct contacts.

Correction to the initial diagnosis: acoustic_weights already preserves H against energy attenuation; only C/D/E/F are reduced by the energy multiplier. The old visible defects were tongue size/root movement and draw order. The existing head still couples H to a relatively wide aperture. Separating articulator contact from jaw opening remains necessary.

The design reference for a raised clear-L blade is Broeders & Gussenhoven's [American English Phonetics, approximants](https://opentextbooks.rug.nl/americanenglishphonetics2/chapter/12-3-1-approximants-l/). Clear L involves tongue-tip contact behind the upper teeth and lateral airflow; dark/vocalized L can differ. This source informs the stylization, and does not verify this speaker's anatomy or any phone boundary. One target cannot represent every L or the dental fricatives.

## Review and construction checks

Outputs: ../../outputs/evan-cartoon-lingual. Native-head before/after and branded continuous-wrist scene both use recording time 2.5–4.5 seconds, 96 frames at 48 fps. Normal clips retain the original audio; quarter-speed clips are muted, 384 frames. All four decode cleanly. The sample-clock waveform/spectrogram/control plot retains unverified aligner labels. No timing, recording or planner weight changed. All 18 previously flagged word regions retain their existing visual review; exact boundaries remain unverified.

Full-resolution 512-pixel heads and selected 1280×720 comparison/scene frames were inspected at little onset/coda, globe L, its rounded vowel, narrow closure and logo L. The smaller blade reduces the protruding-ball appearance and the teeth overlap is clearer. The floor attachment reads better than the rejected isolated blade. Narrow mouth strokes still pinch; the rounded vowel remains mechanically warped; a small cheek texture/shape defect near the ear is present in both baselines during rounding. Fast wide/narrow aperture excursions remain conspicuous. Continuous playback/listening acceptance is not claimed.

33 affected checks pass (lingual, material, solid, rounding, oral layers and FV). They cover root invariance, rising tip, existing control identity, front-tooth occlusion, unchanged closed/FV endpoints, unchanged geometry and nonoral pixels, and prior material/containment regressions. Seven actual-time baseline renders remain pixel exact after extracting the default tongue hook. This establishes compatibility, not performance quality.

export_lingual_psd.py exports four actual editable registered oral layers: cavity, root-floor, blade, upper-teeth. The reopened layer composite differs from the quantized premultiplied reference by mean .002736/255. The transparent PNG is recomposited from layers (ignore cached PSD preview). This is a source-space oral construction plate, not the complete runtime head/character or a verified Moho rig.

## Integration and next work

LingualCartoonSceneBody extends JoinedWristSceneBody; --lingual-tongue selects the study while preserving the continuous wrist, separate index and official branding. Original render defaults remain comparison baselines. The earlier rejected contact-art candidate is excluded.

Next: separate tongue contact/lift and dental identity from jaw opening, using the existing phone catalog and neighboring vowel context. Compare the same little/globe/logo regions and contact releases against waveform evidence before extending duration. Do not hide the contact with an indiscriminate low-energy gate. Then redraw pinched lip contours and design softer neighboring fingers/resting hand. A human character artist/animator is still needed for final anatomy and acting approval. Native 512-pixel raster art and CPU mesh rendering limit detail/iteration; more output pixels cannot supply missing drawings.

Main, V3/V4, approved updater/releases and native projects were not edited; no Moho launch/probe, merge or deployment. Full polished cartoon milestone remains incomplete and the existing heartbeat remains active.
