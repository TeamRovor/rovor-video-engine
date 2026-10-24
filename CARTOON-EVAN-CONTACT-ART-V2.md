# Contact artwork trial: separate lower-lip volume

This development-only study explores a cleaner F/V contact using the selected cartoon likeness. Built-in imagegen edited the existing contact head to add a short upper-incisor shelf, relaxed corners and a peach lower-lip roll. The full source and exact prompt are versioned in `fv-source-v2`. The complete generated head is a construction source, not a replacement character or animation-ready rig.

`build_cartoon_fv_v2.py` registers stable upper-face features to the previous contact source (ECC 0.99866; a registration diagnostic, not an anatomical quality score). It extracts source pixels into three actual working surfaces: lip/contact ink, upper teeth and lower-lip volume. Extraction masks do not procedurally replace the drawn mouth. Registered parts and source hash live in `fv-rig-v2`; previous source/rig folders are untouched.

`SculptedContactHead` is an optional experimental head. It uses the latest material compositor and the original runtime jaw/face/phone targets. Source-space landmarks register the new drawing into those targets. This preserves the current jaw motion, face proportions and timing. Lower-lip volume is kept outside the actual opening; its opacity cannot wash peach skin over the cavity. `contact_parts` exposes the three warped components independently. This is a local raster construction, not a native Moho rig or a hand-drawn anatomical solution.

## Critical comparison

The initial trial changed runtime outer-lip geometry with the new source and made the release bulge. Combining lower-lip volume with the oral interior also produced an unwanted brown patch. That trial was rejected. The final candidate keeps runtime geometry unchanged, separates volume, and occludes it against the opening. Only scratch `../cartoon-lip-art/frames-final` represents the final candidate; earlier Contact/Release experiments are superseded.

At full resolution the held contact has a cleaner, shorter tooth shelf and a subtler lower-lip form. The release remains wedge-like and is not convincingly better animation than the current material head. A nicer generated still is not sufficient evidence of a natural F/V articulation. This candidate is NOT promoted into scene defaults. Broader mouth contours, the tongue/L pose, genuine lip compression and designed in-between shapes still need a character artist/animator. No studio-quality or correct-phoneme claim.

Outputs `../../outputs/evan-cartoon-lip-art` provide same-audio normal/quarter-speed comparison through “favicon” and the following pause (8.25–10.0 seconds), native contact/release/approach comparisons, generated source/exact prompt, registered components and a reopened three-layer PSD. The PSD is source-space construction artwork, not the runtime jaw pose; its mean premultiplied composite difference is 0.000393/255. Neither pixel agreement nor tests establish perceptual quality. Full-resolution selected stills were inspected; continuous playback/listening verification is not claimed.

Acoustic word/phone annotations, planner weights and recording are unchanged. All 18 anchor flags retain prior waveform/spectrogram visual review and exact-phone uncertainty. Targeted tests cover unchanged non-contact poses/targets, mouth-only changes and separated volume occlusion, plus existing F/V/material/solid/rounding regressions. 25 targeted checks pass. Both final films decode without errors: 84 normal frames and 336 quarter-speed frames at 48 fps. Decode evidence is saved with the outputs.

## Continue

Prefer artist-designed contact-to-vowel construction over accumulating more generated full-head variants. Improve the entire lower-mouth contour and tongue anatomy with the selected face proportions locked. The other major defect remains the hook-like resting index and fixed neighboring fingers; clean hand/wrist/shoulder construction before adding incidental motion. CPU raster rendering limits iteration speed, not the required artistic decisions.

Main, V3/V4, approved symlinks/updater and native Moho projects are preserved. No merge, deployment or unattended Moho operation. This is a bounded candidate evaluation, not the agreed polished milestone. Automation stays active.
