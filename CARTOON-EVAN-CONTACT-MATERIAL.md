# F/V release: preserve oral material coverage

The 10.1875-second narrated scene exposed a muddy brown mouth around 8.7917 seconds in “favicon.” Native-head inspection shows the defect during the labiodental contact release: the current planner supplies approximately 0.451 F/V and 0.522 next-vowel weight, with a small rest remainder. The contact artwork and vowel cavity were each faded separately over skin. Even where both drawings are opaque, the combined coverage is (1-f) + f*f, reaching only 0.75 at equal weights. Skin therefore shows through the mouth interior.

`MaterialCartoonHead` is an opt-in compositor over the existing rounded head. It assembles the vowel cavity/teeth/tongue/closure group first, interpolates that premultiplied group with the existing F/V contact group, then places the resulting oral surface over the face once. Shared opaque material stays opaque through the release. Disjoint drawing edges still have partial coverage; this is not a new lip shape or anatomical reconstruction. Pure contact, non-contact poses and all non-F/V blends use the previous exact path. No artwork, landmarks, jaw motion, pronunciation, word/phone times or coarticulation weights change.

The base layered class exposes its original composition sequence as a hook. Its default operation order is retained; seven sampled source times, including the defect and pause, were compared pixel-for-pixel against the pre-refactor implementation. `CartoonMaterialSceneBody` and `render_cartoon_scene.py --material` integrate the optional compositor into the existing scene. Previous scene/defaults remain comparison baselines.

## Review

Outputs in `../../outputs/evan-cartoon-contact-material` contain a native-size same-audio before/after film covering 8.25–10.0 seconds, a muted quarter-speed version, sample-clock waveform, native contact/release/vowel/pause frames, and a branded scene integration still. The old full-scene movie is preserved. No new generated artwork is used.

Full-resolution stills show the overlapping mouth interior darker and more legible during release. The contact plate remains simplified, narrow contours are jagged, and the lower lip/tongue anatomy needs designed artwork. Darkening material does not establish correct phoneme anatomy, perceived fluidity or studio quality. Continuous movie playback/listening verification is not claimed. All 18 word-anchor flags retain prior waveform/spectrogram visual review; exact phone boundaries remain unverified.

New tests check shared opaque material coverage, exact pure/non-contact outputs and confinement of the change to the mouth. Existing tests remain construction safeguards, not a quality score. 118 tests pass. Both final films decode without errors: 84 frames/1.75 s normal and 336 frames/7 s quarter-speed, at 48 fps. Decode evidence is saved with the review outputs.

## Reproduce / next work

Use the checkpoint's Python/dependency paths. Render `render_contact_material_review.py PLAN WAV FRAMES` at 48 fps; its source interval is frame 396 through 479. Normal-speed audio starts at 8.25 seconds in the original narration. Use the same word/phone plan for both columns. For body integration use `render_cartoon_scene.py PLAN FRAMES --material`.

Next, redraw the narrow F/V lower-lip and rounded contours without changing the selected cartoon proportions; add a designed softer hand pose and clean wrist/shoulder construction. Current rest index is hook-like, neighboring fingers fixed, legs static and there is no blink/eye rig. A character artist/animator remains needed for anatomical and performance approval. CPU raster rendering slows iteration; hardware cannot supply missing artwork.

Main/V3/V4, approved symlinks/updater and native Moho projects remain untouched. No unattended Moho operation, merge or deployment. The polished cartoon milestone remains incomplete; automation stays active.
