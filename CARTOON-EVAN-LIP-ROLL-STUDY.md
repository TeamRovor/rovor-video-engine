# Lip compression / jaw source review

This pass did not fix the animation. Four built-in generated source variants were inspected. The revised jaw is genuinely open at its top and no longer includes a neck, but it is not a compatible lower-lip/jaw drawing for the working head.

## Decision

Keep all four sources out of runtime. Compression drawings retain hooked/dotted corners and insufficient lip-roll volume. The exploded upper muzzle still contains a complete mouth. A three-anchor jaw affine fit misses manually authored held-out lower-lip/chin-bend landmarks by 8.47/16.22px at a 512px working head. These are diagnostic author estimates, not measured anatomy or ground-truth accuracy. The native overlay visibly shows the mismatch. No deformation or mask cleanup is being used to hide it.

## What changed

Added source-only jaw registration with explicit anchors, held-out fit evidence, premultiplied sampling and an exact-alpha source-part copy. Corrected alpha inspector overview: it previously stretched wide sheets into square cells. Previews now preserve proportions and save native-resolution opaque light/dark review masters. Original source alpha and hashes remain untouched, including the already-valid legacy teeth.

## Verification and limits

Source-part pixels/alpha match their explicit transparent-gutter region exactly. Native composites are 2172x724, the source size. Legacy tooth hash/bbox remain unchanged. Registration is rejected, not inferred ready from a fitted edge triangle. No new speech film was rendered from incompatible drawings; previous actual voiced normal/quarter-speed Maxillary tests remain the baseline. No phone boundaries changed. No independent listening/continuous-playback acceptance. Main/V3/V4/updater/Moho files and runtime profiles unchanged.

## Next

A human character artist/animator is needed for convincing contact compression and lip roll. Prepare fixed-anchor editable mouth/jaw drawing templates with contact, release and open landmarks and occlusion boundaries. Do not repeat unconstrained full-face generation or scalar placement tuning. Only integrate artwork after matching the upper-lip, lower-lip, cheek/jaw and neck overlaps; then render the same recorded M/B/P-to-vowel and F/V transitions at normal and slow speeds. CPU rendering is available; missing drawings, not hardware throughput, blocked this art pass. Overall polished milestone remains incomplete; automation remains active.

Sources: evan-character/cartoon-v1/lip-roll-study-v1. Outputs: ../../outputs/evan-cartoon-lip-roll. Prior baseline: CARTOON-EVAN-MAXILLARY-STUDY.md.
