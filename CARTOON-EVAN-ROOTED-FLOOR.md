# Optional rooted tongue floor and full reference review

RootedFloorCartoonHead / --rooted-floor extends the optional Duration candidate. The existing broad floor drawing was usable: the distracting worm-like detail came from the raised blade remaining in front of it during ordinary vowels. Reuse the actual two source parts; retract the blade and let the floor cover its base. No new artwork, generated source, whole-face patch, phonetic timing or body acting is introduced.

## Layered articulation

Blade X scale remains .8+.2*H. Y scale becomes .12+.88*ease(H), rooted at native(237,354), versus the former .42+.58*H. Full lift has exactly the old source matrix. Both parts receive the current H-to-oral mesh independently, then the floor composites OVER the blade. Existing cavity/interior clipping and upper teeth still occlude the assembled tongue. Geometry retraction and real layer occlusion replace an always-exposed raised shape; no tongue sprite switch or alpha hide is added.

This is authored2D articulation. H still serves L/TH/DH, so separate dental/lateral constructions remain unfinished. At sampled vowels416/434 and rounded150 the source now reads as a broad simple floor; at145/147 the raised tip remains visible behind the incisors. The selected cartoon drawing/likeness and palette remain. A human character artist/animator must approve anatomy and performance; this is not studio-ready.

## Sampling workflow

cartoon_head.warp is factored into unchanged warp_maps and sample_warp operations. Defaults remain uncached. The new profile uses a four-entry per-head inverse-field LRU keyed by ALL source/target point bytes, dtypes/shapes and sample scale. Dynamic image pixels are sampled anew on every call; no rendered head, pose or movie frame is cached. Current1x/2x fields use at most32MiB per head. The same oral map can serve cavity/rim/matte and both tongue parts.

Three actual pre-extraction Duration images at129/145/416 remain pixel exact after factoring; cached Duration output also matches those images.13 targeted checks pass (8new+5duration): fixed root/full-lift matrix, low-blade floor coverage, retained raised tip, exact rest/bilabial/FV poses, cavity/teeth occlusion, dynamic-image cache separation, point/scale invalidation, bounded eviction, five exact pure cache poses and existing duration safeguards. Counts/round trips are implementation evidence, not artistic quality.

The full renderer writes per24-frame progress and source/plan fingerprints for four disjoint frame ranges. Diagnostic tongue coverage is BEFORE the lip matte/material gates. It does not measure visible anatomy or sync accuracy. The local machine reports8GiB RAM/8logical CPUs; this path uses CPU raster warping, not native Moho. Four sampled workers used about118–148MiB RSS each. Duplicate baseline rendering was stopped after useful comparison frames were retained, prioritizing the revised shot. No wall-speed multiplier is claimed from cache hit counts.

## Review and construction exports

Target reference is0–10.1875s through the complete first narration question/explanation and pause, with word-anchored point accents, anticipation/holds/settle and the official Rovor mark/browser-globe example. Frame count489 at48fps; quarter-speed1956frames is muted and repeats source frames. Both final films decode cleanly (489/1956frames); normal audio also decodes cleanly. All489 tongue surface rows are valid, with no dental/FV/rounded fallback. Cache2507hits/1660misses, max4entries. Media/decode/provenance results are in outputs/evan-cartoon-rooted-floor-full/Review-Evidence.json. Temporary idle-sleep holds ended automatically with export. Selected full-resolution native-head and whole-scene frames are critically compared; continuous playback/listening acceptance is not claimed.

Two reopened editable PSDs contain actual blade/root-floor layers, floor in front, at low/lifted H-source construction states before lip/interior masking. They are not full head/body rigs or native Moho projects. Round-trip mean premultiplied errors: lifted .000920/255 globally and .208878/255 over supported pixels; low .0000921/255 globally and .025950/255 locally. Transparency makes global errors alone misleading. Source PNG hashes are unchanged.

The cleaner tongue does not repair the heavy lower lip/corner spurs/plain tooth strip, independent chin, missing eyes/blinks, held open palm, static neighboring fingers/legs or limited two-point acting. Short-vowel duration undershoot still needs stressed-accent review against the voice. Exact phone boundaries remain unverified despite earlier VISUAL waveform/spectrogram review of all18 flagged word-anchor rows. No retiming is justified by coverage alone.

## Next bounded work

Assess the complete normal-speed shot, then separate L versus TH/DH tongue/dental shapes and improve the inner lower-lip aperture from consistent source drawings. Preserve contact timing and the selected cartoon identity. Improve specific full-shot acting defects; do not keep adding source plates or profiles without a visible reason. Main/V3/V4/updater/approved symlinks/native projects remain unchanged. No merge/deployment or unattended Moho. Full polished milestone remains incomplete; recurring development stays active.
