# Relaxed F/V contact candidate

The new opt-in FVContactHead replaces the old arched grimace with a narrower, relaxed contact drawing split into lip/outline and upper-teeth surfaces. It retains the existing independent brows, jaw/face mesh and acoustic plan. Non-F/V pure poses and the upper face are preserved in regression checks. LayeredCartoonHead and prior expressive/body routes retain their old contact; this candidate is not an approved-release replacement.

## Source and rig

Built-in imagegen edited only the mouth on the neutral cartoon reference. fv-source preserves the source and exact prompt. Stable upper-face registration gives ECC 0.99908, which is a diagnostic correlation and not anatomical confidence. Only the local contact surfaces are extracted; generated whole-head pixels do not replace Evan's face. fv-rig contains lip-contact, upper-teeth, contact mask, geometry, source hash and limitations. animationReady=false.

FV geometry now uses narrower, near-horizontal corners, a shallow opening and the neutral chin anchor. Lip and tooth layers warp separately. The fading contact target is capped to a 15-pixel mouth height so it does not inflate into a broad vowel cavity during coarticulation. The same existing F/V weights drive the candidate; no phone, word, pronunciation or audio timing was changed. Default geometry/contact lookup was generalized per instance while preserving old defaults. New and old rig instances can be compared in the same process.

CartoonFVBody and render_cartoon_gesture_study.py --fv-contact integrate it with the current layered body, brows and hands. The three-layer PSD contains a posed clean face/brow backing and separate contact lip/upper-teeth drawings. It is reopened and layer names verified; runtime deformation stays in code, not native Moho bones.

## Review

The side-by-side normal and quarter-speed diagnostic uses exactly the same source recording and times on both heads. It makes a labeled review cut between the opening (0–0.729167 s, including V in ever) and missing a favicon (8.1875–9.375 s, including F and V). These are test excerpts, not a finished narrative edit. 92 frames at 48fps make a 1.916667-second normal film. Native comparison also shows V in of at 4.23 s. Source, peak and neighboring transition frames at 0.25/0.34/0.417 and 8.56 s were inspected at full resolution, along with the body CLI integration frame.

The old grimace is visibly reduced. The new contact reads calmer and keeps the jaw less tense, but the rolled lower-lip anatomy is still simplified and can read as a narrow tooth hint. This is not a ground-truth depiction of this speaker's F/V, and an experienced character artist/animator should review/redraw that contact before production acceptance. Source contact art has limited native pixels; export scaling cannot add lip construction. Other vowel/tongue shapes still need performance review. Neck/wrist joins, shoulder creases, hand linework and broader face acting remain unfinished. The 18 timing flags retain visual review with exact phone boundaries unverified.

89 tests pass, including old non-F/V pose preservation, stable upper face, separate/local lip and tooth layers, and non-inverting new geometry across all pairwise pose blends. The subsequent constrained-contact geometry sweep also passes. Tests establish rendering safeguards, not perceptual fluidity or studio quality. Local outputs/evan-cartoon-fv contains normal/slow comparison, native peaks, editable source layers and a body integration still. Main, V3/V4, approved releases/updater and native Moho are untouched; no native probe, merge or deployment.

Next: artist-reviewed rolled-lip cleanup and L/tongue articulation, then a longer scene combining these contacts, a real pause and the authored body gesture. Keep the old and new contact baselines; do not treat this small anatomy improvement as a completed professional performance.
