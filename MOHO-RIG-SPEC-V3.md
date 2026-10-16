# Evan V3 — Reference-faithful Moho rig specification

This is a production handoff for the **next stage**, not a claim that a complete Moho rig is built. The V3 reference-raster video renderer works independently of Moho. These are the exact layers, joints, and acceptance criteria required to achieve comparable **reference accuracy** with fully articulated character movement.

## Non-negotiable visual identity

Use `evan-character/references/evan-personality.png` and `evan-rig-reference.png` as the character's visual source of truth. Preserve (1) expressive medium-brown tousled hair, (2) black rectangular sunglasses with a slight tilt, (3) defined jawline and goatee, (4) natural warm skin-tone shading, (5) dark navy collared shirt with realistic fold highlights, (6) black necktie and black pants, and (7) recognizable shoulder/torso proportions. **Do not create a new generic face or flattened cartoon hair.** Trace individual layer artwork only when the original shapes, texture and tone can be preserved. Do not borrow an unrelated cartoon style.

## Rig layer inventory (must be independently editable)

### Body core

- `00_Root`: overall character transform, scale, flip and Y translation.
- `01_Hips_Pelvis`: pelvis shape and belt, primary hip pivot.
- `02_Torso_Shirt_Base`: ribcage/navy shirt base, independent body lean.
- `02a_Torso_Fold_Overlay`: shirt crease artwork moves with the torso.
- `03_Neck`: skin shadow under jaw, parented to torso.
- `04_Collar_Left`, `05_Collar_Right`: layered over neck and under face.
- `06_Tie_Knot`, `07_Tie_Blade`: loose pivot for secondary tie sway.
- `08_Legs_L/R`, `09_Shoes_L/R`: required for full-body scenes.

### Arms & hands

Create equivalent nested groups for L and R:
`UpperArm_Art > Forearm_Art > Wrist > Hand_Switch`.
Separate left/right shoulders, elbow pivots, cuffs and forearms. Paint or overlap under-sleeve seam areas so the joints never reveal gaps. `Hand_Switch` poses: relaxed, open palm, pointing, index-up, thumbs-up, fist. Avoid scaling five-finger hands until details disappear.

### Head and expression

- `Head_Base_Skin`, `Jaw_Outline`, `Left_Ear`, `Right_Ear`.
- `Hair_Back`, `Hair_Main`, `Hair_Foreground_Clumps` — separable so subtle secondary motion doesn't flatten the hairstyle.
- `Goatee`, `Moustache` — preserve style, location, and jawline.
- `Sunglasses_Frame` and `Lens_L/R`, including original frame highlights.
- `Brows` behind/above sunglasses for skeptical/concerned expression.
- `Nose_Highlight`, `Cheek_Shadow` for face volume.
- `Mouth_Switch` — nine shapes with matched lip-anchor, skin and shading from the supplied original rig reference.
- `Face_Switch` — confident, amused, talking, skeptical, excited. Switch artwork must match head size, center and angle to avoid frame-to-frame popping.

## Bone hierarchy

```text
Evan_Root
├── Hips (body center / anchor)
│   ├── Left_Leg → Left_Knee → Left_Shoe
│   ├── Right_Leg → Right_Knee → Right_Shoe
│   └── Torso
│       ├── Collar + Tie (secondary motion)
│       ├── Left_Shoulder → Left_Elbow → Left_Wrist → Hand_Switch
│       ├── Right_Shoulder → Right_Elbow → Right_Wrist → Hand_Switch
│       └── Neck → Head
│           ├── Hair (subtle independent drift)
│           ├── Glasses + Brows
│           ├── Expression_Switch
│           └── Mouth_Switch
```

The default facing is the near-front 3/4 reference, not a hard symmetrical front view. The attached pose cutouts must not be mistaken for completed limb layers.

## Rhubarb → Moho mouth setup

Rhubarb produces A, B, C, D, E, F, G, H, X. Label Moho switch layers with those exact names; a simple import script can place keyframes at Rhubarb's returned start times, with X for silence. V3's current raster rendering maps each Rhubarb cue to the nearest extracted mouth illustration:

| Rhubarb | V3 sprite |
|---|---|
| X | rest |
| A | MBP |
| B | AE |
| C | L |
| D | open |
| E | O |
| F | O |
| G | FV |
| H | UW |

These are **approximate** visual mappings, not a perfect professional phoneme set. Hand-repaint the nine shapes for the final Moho rig at a consistent 3/4 perspective while preserving Evan's lips, moustache, beard, and skin shading.

## Motion style and cadence

- Base output: 720×1280, 24 fps. Full-body and bust crops should share comparable apparent head size where possible.
- Natural head idle: about 1–2° lateral motion over 3–5 seconds; avoid constant rhythmic head-bobbing.
- Blink only if eyes are actually drawn behind sunglasses in a future version; fake black lens 'blinks' are visually incorrect.
- Gesture intent should lead the spoken keyword, not lag by 0.5 seconds. Hold a pointing pose long enough to identify the illustrated element.
- In between actions, favor 6–12-frame eased transitions, modest shoulder movement, subtle hand follow-through; keep feet/hips planted during talking-head scenes.
- Match emotion to the *meaning* of the sentence; do not randomize facial expression every second.

## Background / topic illustration standards

Illustrations can be simple as long as they are topic-specific. A favicon explanation should show real tabs, identity marks, and before/after states. A store explanation should show product pages and checkout rather than generic business icons. Rovor Digital branding may appear, but it must not overpower the lesson. No false customer statistics, fabricated customer screenshots, fictitious testimonials, invented results, watermarked stock, or unapproved external logos.

## Quality gate before scaling to 100 Shorts/month

1. **Likeness:** Is Evan instantly recognizable relative to the approved sheet? Any 'generic sunglasses guy' fails.
2. **Artwork:** Are hair and shirt details intact at mobile resolution? Are skin/mouth mattes clean, without visible cutout seams?
3. **Lip-sync:** Does speech consistently match mouth timing, including closed lips for M/B/P and rest during silence?
4. **Gesture continuity:** No hand teleports, frozen shoulders, broken elbows, disappearing cuffs, or abrupt whole-body swaps.
5. **Narration accuracy:** Does every major illustration demonstrate the statement actually being said? A keyword match is only a starting point.
6. **Readability:** Titles/captions visible within mobile safe area, with no spelling errors or clipping.
7. **Export:** Correct aspect ratio, continuous audio, no missing frames, consistent branding and end card.

**Next real milestone:** Build one highly accurate, native Moho character master with switch layers and joints; animate the existing 22-second favicon script. Only after that pass should the long-form pipeline be expanded.
