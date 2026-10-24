# Bounded samples before head compositing

The prior cheek fix exposed legacy cubic-sampling lobes outside valid premultiplied RGBA ranges. Negative coverage or alpha above 255 was reaching alpha-over operations; foreground coverage could subtract underlying face paint. This pass bounds the sampled head surfaces before those blends. It is renderer maintenance, with a subtle visible edge correction, not a meaningful animation-quality milestone or new mouth artwork.

## Implementation and scope

LayeredCartoonHead now routes face/cavity/teeth/lips/contact sampling through sample_surface / constrain_surface. FVContactHead applies the hook to its lip and teeth components before combining them. Layered/Lingual tongue code also constrains the affine sample before converting it back to straight RGBA, and constrains each registered floor/blade sample before combining them. Default constrain_surface returns its input unchanged; existing modes retain their rendering.

BoundedCartoonHead extends AnchoredCartoonHead and enables bounded_premultiplied. Negative coverage becomes zero with zero RGB. Coverage above 255 is rescaled together with RGB, preserving positive-alpha straight colour rather than brightening ink by clipping alpha alone. RGB is then limited to the valid premultiplied range [0, alpha]. Valid finite premultiplied samples remain exact. The inputs are finite image samples; this is not a general nonfinite-data recovery routine or a linear-light renderer conversion.

BoundedCartoonSceneBody / render_cartoon_scene.py --bounded-head integrates the opt-in head on the existing articulated body. This change covers sampled head skin/oral/FV/tongue surfaces and pre-composite tongue-affine samples. Body and brow sampling are unchanged; do not claim global engine-wide range enforcement. No source art, mesh targets, timing, recording, alignment annotation or phoneme weight changed.

## Evidence and critical review

51 affected checks pass: six new bounded-sample checks plus anchored skin, separated jaw, tongue, material, solid cavity, rounding, FV and oral regressions. They cover exact valid samples, input nonmutation, positive-alpha colour preservation, negative/zero coverage, RGB overshoot, uint8 input, actual component/pre-composite/output ranges, geometry and closed-mouth coverage. Seven baseline actual-time renders remain pixel exact after surface-hook extraction.

An audit of 135 actual sampled surfaces (nine pure controls and six recording times) finds 50,668 invalid pixel samples before correction and zero afterward. Alpha extrema change from -41.2608…301.9288 to 0…255. These count repeated sampled surfaces, not distinct on-screen defects or an artistic score. Surface-Audit.json retains before/after component statistics. Review-Evidence.json separates raw straight-RGBA differences from visible differences composited over the review paper; hidden RGB changes must not be presented as visible improvements.

Outputs ../../outputs/evan-cartoon-bounded-surfaces. Same-audio native-head comparison and branded integration cover source 8.1875–10.1875 s, “missing a favicon” and the pause. Each normal clip has 96 frames at 48 fps with original audio; each muted quarter-speed clip has 384 frames, repeating original frames rather than inventing in-betweens. All four completed films decode cleanly. Full-resolution head pairs at rounded vowels, bilabial closure, F/V release and pause were inspected. The visible change is small; the gray/pinched contact construction and mechanically warped rounded lip silhouette remain. No continuous playback/listening acceptance is claimed.

The selected entertaining cel-cartoon direction and official branding remain intact. No generated bitmap or flattened sprite replacement was used. All 18 flagged word-anchor rows retain their waveform/spectrogram visual review and unverified exact phone boundaries; this edge fix provides no new phonetic accuracy evidence.

## Next work / limits

Prioritize artist-designed clean shallow-contact and rounded-vowel contours, then separate L/dental tongue construction and independently timed jaw/chin motion under lip seals. Existing H is shared by L/TH/DH and already survives energy attenuation; do not reintroduce the old false diagnosis or suppress contact based on volume. Human character-art/animation review is still needed for final anatomy and performance. Neighboring fingers/resting palm, shoulders, static legs and missing eyes/blinks remain unfinished. CPU raster rendering limits iteration speed; higher output resolution cannot supply missing drawings.

Main, V3/V4, approved releases/updater and native Moho projects are preserved. Development commits only; no merge/deployment or unattended Moho action. The full polished cartoon milestone is incomplete and the existing heartbeat remains active.
