# Optional shallow F/V contact study

Evan's old F/V contact reads as a narrow slit. `PlanarFVCartoonHead` / `--planar-fv` extends the optional OccludedTeeth candidate with a newly drawn shallow contact. This is an unfinished source/placement study, not the polished cartoon milestone or a new default.

## Artwork and working components

Built-in imagegen used the selected cartoon design sheet as style reference. Initial contact-v1 and its v2 edit read as grins; a separate v3 generation had excessive upper-lip bulk. Editing v3 to remove that bulk produced chosen contact-v4. A further edit replaced only the incisors with dark cavity underpaint. Exact prompts, original images, hashes and generation graph are in fv-source-v3 and fv-rig-v3/manifest.json. The raw generated plate is not a rig.

build_planar_fv_art.py extracts two actual transparent canonical components: lip-contact (with generated underpaint only beneath the extracted teeth) and upper-teeth. Registration fits source bounds into [198,317,274,331] in native 512 head coordinates; this authored fit is not anatomical calibration. Nearly opaque alpha >=250 is snapped to255 before separation. Both components are premultiplied, resampled at4x and reduced. Reassembly versus the registered source has mean premultiplied error0.001229/255 globally,0.492607/255 over source-support pixels; global transparency makes the first number misleading alone. Editable two-layer PSD is exported and reopened; mean composite error0.00007991/255. The teeth layer includes its small boundary guard; this is not a full dental model.

At runtime the two actual components share a rotation/uniform-scale/translation parent from current mouth-corner endpoints. Jaw aperture cannot independently squash or inflate this contact art. Separate native jaw/skin, cavity, tongue and body controls remain inherited. F and V still share one pose; teeth do not yet have an independently animated contact joint. This adds no measured anatomy or phonetic accuracy.

## Evidence and defects

Twelve targeted tests pass: six new placement/locality/layer checks and six existing tooth-occlusion regressions. Eight non-G pure visemes remain pixel exact versus OccludedTeeth; G intentionally changes. Across489 source-clock samples jaw/face targets are exact; minimum plane determinant0.176753, maximum uniform-matrix error0.000001799,34 active contact samples. These establish implementation properties, not animation quality.

Normal and muted quarter-speed native-head comparisons and branded scene shots cover original recording8.1875–10.1875s (“missing a favicon” through pause),96/384frames at48fps; all four decode cleanly, no contour fallback. Inspect full-resolution contact411/420, transition414/422, following-vowel426 and branded integration. No continuous playback/listening acceptance is claimed.

The new pose shows short central incisors/lower-lip contact more clearly than the slit, but still hints at a smile and has a heavy lower lip/corner creases. At414 and422 the existing alpha blend reveals two overlapping lip contours as the contact releases to the vowel. At426 the common following vowel is unchanged. Therefore do not promote this candidate or call it smoother/studio quality. The source study makes the failure concrete; it does not solve continuous mouth topology. Selected concept style/likeness is retained broadly, but final lip anatomy needs a character artist.

## Next bounded work

Replace the mixed F/V-to-vowel double contour with shared outer-lip correspondence and an occlusion-controlled incisor/lower-lip transition, retaining acoustic weights and exact non-contact output. Use frame414/422 as failure cases. Do not hide the defect with a whole-face patch or simply shorten the audio contact. Then assess B seals, distinct tongue poses, independent chin response and eye/blink/finger acting. CPU raster/source resolution limits iteration/detail; a human animator must approve anatomy and performance.

Main/V3/V4/updater/native projects remain preserved; no merge/deployment or unattended Moho operations. Full milestone remains incomplete; recurring development stays active.
