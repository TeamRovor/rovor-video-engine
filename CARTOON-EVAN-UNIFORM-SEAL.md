# Bilabial-only drawn seal: unapproved artwork study

The original closed-lip drawing has a hooked right corner which becomes an ink spur when compressed into M/B/P. Three built-in imagegen source iterations explore a separate pressed-lip seam and a detached lower shadow, using the selected cartoon concept/full-head context, not a photograph crop. v1 is too ribbon-like; v2 is too faint and changed the resting expression. v3 is flatter and darker, used only for the optional A-channel seal experiment. Native contrast is still weak. Do NOT promote this profile or claim it solves the popping open/closed transition.

## Actual components / runtime

lip-seal-v1/source/seal-source-v1/v2/v3.png are generated SOURCE PLATES, not registered rig drawings. Exact prompts/reference graph are in source/Prompt-Set.json; generated alpha is retained. register_lip_seal.py identifies the two disconnected opaque marks, splits at the transparent horizontal gap, and registers seam.png and lower-shadow.png as separate512px parts. This is pixel separation/placement, not a repaint or skin-colored patch. The seam endpoints map to original rest corners(194,326)/(280,314); the lower shadow is independently placed3nativepx below the seam centroid. AREA minification of premultiplied pixels then2x LINEAR placement/AREA reduction avoids direct minification aliasing. manifest.json records source hash/endpoints/split/transforms/part hashes.

UniformSealCartoonHead / --uniform-seal extends the independent-chin profile. The two source parts follow one uniform mouth-corner parent, so jaw height/chin changes cannot crush the drawn stroke. Original selected resting smile remains EXACT. Only normalized A weight(M/B/P) interpolates from old closed source to the new seal parts. Existing closed/cavity visibility, jaw/rounding/tongue/FV geometry/material timing remain unchanged. This is component color interpolation, not continuous anatomical lip topology; two different lines can still overlap in an inbetween. All pure non-A controls are exact. Defaults unchanged.

The small Layered.closed_surface hook delegates the prior sampling call unchanged; pre-refactor native0/680/742 images matched pixel exactly after extraction. No source, release, updater or native Moho project was modified. The two-plane PSD is registered construction only, before dynamic placement/A mix/visibility gates, NOT a full head or native character rig.

## Critical finding / next work

The hook is reduced at strong M closure, but a thin line replacement does not fix the sharp release into the following open/rounded vowel. Existing cavity opacity fades and the old/new line blend remain. Native contrast is weaker than the original cartoon ink; source geometry is still an imagegen approximation rather than coordinated lip/inner-lip/jaw drawings. Keep this study unapproved. A human character artist/animator is needed for consistent seal and open-lip inbetweens/performance approval.

Audit the rounded AO in “small” against the original voice next: the existing duration budget only covers C/D vowels, while this short rounded gesture bypasses that budget. This is a suspected control gap to investigate, NOT a reason to retime the aligner or add global smoothing. All18flagged regions remain visually reviewed/exact-boundaries-unverified. The B/M diagnostic film retains original audio and source times; no listening or studio-quality acceptance.

Eyes/expressions and broad hand acting remain unfinished. Full polished milestone is not complete; automation remains active. Main/V3/V4, approved symlinks/updater and native Moho preserved. No merge/deploy.
