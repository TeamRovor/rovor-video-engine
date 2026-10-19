# Optional shared F/V oral contour

The planar contact study showed doubled outer lip contours at source frames414 and422: the F/V contact and vowel had different silhouettes when alpha blended. `CorrespondentFVCartoonHead` / `--correspondent-fv` extends that optional study with common drawn-envelope correspondence. It retains all existing source art and acoustic weights.

## Construction

The existing contour_maps helper traces each oral construction's largest50%-alpha contour at4x, casts256 rays from its centroid, and interpolates centers/radial envelopes by the current F/V weight. Both constructions move to that shared envelope before mixing. This is radial silhouette correspondence; it is not anatomical lip topology, measured speaker anatomy or new phone alignment.

Cavity, teeth, tongue and closed lips remain separate working surfaces. They each receive the vowel's same inverse field before assembly, retaining their parent registration. The F/V lip/teeth construction receives the contact field. Linear sampling of bounded premultiplied surfaces avoids cubic overshoot. The face/skin is not remapped by this step. The new blend is confined to the original largest opaque oral-contour bounds plus a3px antialias margin; outside that rectangle the old oral blend is retained exactly. This prevents minute distant alpha dust from changing unrelated skin by one quantization step. An initial locality check exposed four such pixels; the guard was added before final rendering. Pure contact and zero-contact states delegate exactly to PlanarFV; unsupported contours fall back to that existing compositor and increment a separate counter. The old default and earlier optional modes remain unchanged.

No new imagegen calls or source pixel edits are involved. Actual fv-rig-v3 components, generated sources, exact prompts/hashes and editable PSD remain as recorded in CARTOON-EVAN-PLANAR-FV.md.

## Review

Ten targeted checks pass (four new +six prior PlanarFV checks), including all9 exact pure controls, local change, silhouette mismatch reduction, valid surfaces and degenerate-reference fallback. Across489 jaw/face targets maximum difference0;34 mixed-contact samples register without FV/rounded fallback. Aggregate50%-alpha silhouette disagreement falls29419→1919pixels;414:779→48,422:570→49. These measurements precede the locality guard and describe oral envelopes, not artistic/phonetic accuracy.

Before/after native512px heads and branded1280x720 integration cover source8.375–9.375s, “a favicon” through its pause. Normal48frames at48fps use the original recording; muted quarter-speed versions contain192frames. All four final films decode cleanly;18 mixed samples in the review have no fallback. Selected contact, release and settled frames are inspected at full resolution; continuous playback/listening acceptance is not claimed. See outputs/evan-cartoon-fv-correspondence/Review-Evidence.json and Contact-Contour-Audit.json for this pass's measured results.

At414 and422 the obvious second outer lip edge is reduced compared with the previous source/placement study. The drawn lower lip still looks heavy at high F/V weights; tiny corner spurs, the narrow tooth strip and internal contact/vowel colour interpolation remain. Common outer silhouettes do not establish correct incisor/lower-lip contact or smooth temporal acting. All source poses are artist-authored approximations; F/V still share one drawing. This remains optional and animationReady:false, not studio-quality acceptance.

## Next bounded work / safeguards

Review whether the remaining interior tooth/lower-lip transition reads as a true contact release. Give the existing tooth component an independent contact/occlusion control behind the lower lip rather than treating a common outer envelope as sufficient. Preserve the exact non-contact/pure endpoints and acoustic timing. Then assess bilabial seals and distinct L/dental tongue poses; independent chin, expressive eyes and softer neighboring fingers remain unfinished. CPU raster/source pixels constrain detail and iteration; a character artist/animator must approve anatomy and performance.

No merge/deployment or unattended Moho operation. Main/V3/V4/updater/approved releases/native projects remain preserved. The full polished cartoon milestone remains incomplete and recurring development stays active.
