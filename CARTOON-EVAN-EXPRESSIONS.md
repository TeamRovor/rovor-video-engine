# First independent eyebrow acting controls

ExpressiveCartoonHead adds two genuinely separate original eyebrow drawings above the existing separate oral surfaces. They have independent vertical raise and pivot rotation controls in pixels/degrees. Generated artwork supplies only hidden forehead skin beneath the old ink; hair, sunglasses, nose, ears, mouth, jaw and silhouette remain the original rig. This is a restrained brow component, not a complete expression rig or a replacement set of flattened head sprites.

## Source and registration

Built-in imagegen removed the brows from a visible square neutral-head reference. expression-source contains the input, output and exact prompt. build_cartoon_brows.py registers stable hair/glasses/nose/mouth regions, excluding the brows, at ECC 0.99950 (a correlation diagnostic, not confidence). Only the original brow footprints and small feather margins use the generated skin, with a measured skin offset [-5,-2,-1]. Original ink is separated into left/right alpha layers; a foreground mask keeps brows behind the original hair and glasses. expression-rig saves the layers, repair/occlusion masks, pivots, source hash and limitations. animationReady remains false.

The renderer initially introduced subpixel color rounding outside the forehead. A regression caught it; final composition explicitly copies all pixels outside the editing mask from the original oral-driven result. Both the changing mouth and other features are now byte-exact outside the forehead in the regression. Original LayeredCartoonHead remains unchanged.

## Acting and integration

Cues for the first occurrences of ever, tiny and here are explicitly authored accents, timed from the aligned words. They approach, hold and release through continuous curves. They do not infer emotion automatically from an acoustic model or animate on every phoneme. Cues are exported with word/script indices. Independent right lift and opposing left tilt make an asymmetric emphasis; occasional two-brow raises support the opening question. Range is capped at eight pixels/degrees.

CartoonExpressionBody composes the new head with the existing local-underarm body/hand rig. Use render_cartoon_gesture_study.py --expressions; old routes/defaults remain available. A full-resolution body integration still accompanies the native head diagnostic. render_cartoon_expression_study.py renders 231 frames at 48fps with the original narration and official Rovor branding. The existing mouth plan is unchanged. A reopened three-layer PSD contains browless-head, brow-left and brow-right pixel artwork; runtime hair/glasses occlusion and animation controls remain in code, not native Moho bones.

## Critical review

Native neutral/acting comparisons at 0.35, 2.40 and 3.60 seconds were inspected with solid backgrounds, alongside the body integration. The asymmetric accent is readable in close-up; it is subtle in the wide body shot. Hair and sunglasses leave very little forehead travel, so larger raises are clipped. Some brow edge/skin transitions remain rough. This source needs more expressive construction art, or artist-reviewed forehead/hair adjustments, to support a wider acting range. Eyes remain hidden by opaque sunglasses; no blink or eye rig is claimed. Head perspective, cheeks, nose and emotional jaw changes are not independently authored yet.

The comparison visibly retains the bad F/V grimace around 0.35 s. Brows do not fix it. Neck/collar, wrist, hand linework, residual shoulder creases and tongue acting also remain unfinished. The 18 speech flags have prior visual evidence review, with exact phone boundaries still unverified. This is not polished or studio-ready animation. A character artist/animator is still needed for anatomy and performance review; CPU export speed is secondary to missing drawings/acting.

85 tests pass, including independent brows, preservation outside the forehead, word-anchor use and continuous control curves. Actual source/registered/native assembled views and body integration were inspected. Normal/quarter-speed diagnostic films, native comparison, cue record and editable PSD are in the chat outputs/evan-cartoon-expressions directory. Tests do not establish perceptual acting quality. Main, V3/V4, approved updater/releases and native Moho are untouched; no merge, deployment or native probe.

Next: replace the F/V contact grimace with a designed lower-lip/upper-teeth contact and review it against actual narration; then clean neck/wrist joins and develop broader animator-reviewed expressions. Preserve this restrained brow baseline instead of enlarging excursions into clipped hair.
