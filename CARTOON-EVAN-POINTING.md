# Separate hand drawings and narration pointing study

The new opt-in `CartoonGestureBody` retains the cartoon head, torso and acoustic speech plan while separating both hands from the forearm meshes. Original open hands and one generated right-screen pointing drawing attach through the hierarchical hand-bone transform. Wrist pivots move from the old palm-centered coordinates to manually inspected wrist locations: left [214,762], right [810,762]. The forearm retains a short overlapping wrist band. The previous CartoonBody and its films remain an unchanged comparison baseline.

## Source versus working component

Built-in imagegen created hand-source/right-point-v1.png using the cartoon setup as a style reference. The source shows one extended index, three curled fingers and a thumb. It is not a whole-character replacement or a new full-body pose. The generation prompt is saved beside it. build_cartoon_hand.py registers it with a manually inspected wrist/axis transform into hand-rig/right-point.png, with source hash, matrix and limitations in manifest.json. Registration is explicit manual placement, not a fabricated image-similarity score. animationReady remains false.

Native assembled review exposed an oversized wrist-stub flap under the forearm. The overlap was shortened from 42 to 18 source-canvas pixels and the final assembly inspected again. The large flap is reduced; a wrist contour/color transition remains visible at close range. The new hand's outline is thinner and its closed palm is more compact than the original open hand. It needs artist cleanup before production use. Fingers belong to one alternate pixel drawing; they are not individually articulated.

Pose selection is discrete: the runtime never dissolves two sets of fingers. This shot uses the pointing drawing throughout, anticipating and raising it toward the browser card as the narration reaches tiny/little/globe/sitting/up here. It does not demonstrate a finished open-to-point finger transition. The browser card is lower in the composition so the held index direction runs toward the favicon area. Both shoulders, elbows and wrists retain continuous authored motion and follow-through. The six-layer PSD holds actual torso, separate hands, separate forearms and head at the gesture pose; its reopened composite matches the layer assembly (mean premultiplied difference 0.00576/255). Bones remain in code/metadata, not in the PSD or a verified native Moho project.

## Review deliverables

The chat outputs/evan-cartoon-pointing directory contains the 4.8125-second 48fps narration shot, a muted quarter-speed version, native open/point comparison on the same arm controls, stage frames and editable PSD. The original 231-frame open-hand film remains in evan-cartoon-body-rig for comparison. Compare full-resolution wrist/shoulder contours as well as normal/slow motion; frame count is not a quality rating.

79 checks pass, including no forearm triangle foldovers throughout the stronger gesture, hierarchical wrist attachment, removal of original fingers from the forearm layer and identity resampling of a rigid hand. The PSD is saved/reopened and checked. Native source/component and full-resolution stage frames were inspected. These checks establish useful component behavior, not convincing acting or accurate anatomy.

## Remaining limits and next work

The original armpit folds still duplicate under shoulder rotation, and the neck/collar transition remains imperfect. No new hidden shoulder/neck artwork has been accepted on this pass. The source's low-alpha edge speckles remain visible against white in the editable preview. The upper face still lacks independent brows/blinks; lips/FV and tongue acting need artist cleanup; legs are static. The 18 timing flags retain visual review with exact phone boundaries unverified. Source hand pixels are rescaled into the rig; a larger export cannot replace missing construction art. CPU rendering is an iteration cost rather than a solution to these drawing defects.

Next: get genuinely registered hidden shoulder/neck artwork and clean the hand linework/wrist contour; add a relaxed hand and a designed finger transition only after those surfaces assemble cleanly. A character artist/animator is still needed for production anatomy and acting review. Preserve main/V3/V4, approved releases/updater and native Moho; no merge/deployment or unattended Moho probe was performed.
