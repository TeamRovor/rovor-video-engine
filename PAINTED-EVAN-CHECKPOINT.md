# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. The original photo supplies loose identity cues only. Follow CARTOON-EVAN-DIRECTION.md and cartoon-v1/source/design-sheet-v1.png; the painted-realistic direction is superseded. Preserve hair, sunglasses, navy shirt/black tie and official Rovor branding. Do not replace the character with geometric mouth patches or a flattened full-character sprite.

Checkout work/engine, branch development/evan-painted-rig (historical name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4 remains based on experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Main remains 4e099b5f1a30661c952358f49e1e2d70a5fe2a62; V4 known 27b664b9daa924ff17d3b874264bc4cef7131196. Preserve V3/V4, approved symlinks/updater and native projects. Do not launch/restart/probe Moho unattended after its earlier crash.

Automation develop-evan-painted-animation stays ACTIVE. Notify only on meaningful review milestones/failure/completion/required action. Make routine decisions autonomously. Disable only when the full polished cartoon milestone is actually ready for review. It is NOT complete.

## Current working construction

All new modes are opt-in; original defaults remain baselines. Source artwork, registered components and runtime controls are distinct. Existing folders: head-rig-v2, oral-rig, body-rig, hand-rig, socket-rig, expression-rig, fv-rig, neck-art-rig, index-rig and new wrist-rig.

- Head: separate skin/cavity/teeth/tongue/lips; original independent brows. FVContactHead uses registered relaxed contact surfaces; SolidCavityHead keeps the opening solid and tilted closure intact. RoundedCartoonHead separates phone-driven lip width from audio-driven jaw, with authored shape-only ±62.5 ms lead/release. MaterialCartoonHead interpolates oral groups before placing on skin, avoiding skin exposure during F/V release. No new acoustic timing claims.
- Neck/collar: independent registered neck under fixed collar; pale gaps closed in native tilt/jaw checks, residual angular fold. Shoulder joins still need cleanup.
- Body: independently controlled arm/wrist chains. One index has three phalange controls, remaining thumb/three neighbors share a drawing. CompactIndexRig / CompactCartoonSceneBody scales resting bends and projected segment lengths to 70%, preserving full point pixels. Rest is still clenched, not a designed naturally relaxed hand.
- Scene: 0–10.1875 s through favicon and its pause, two word-anchored gestures with anticipation/holds/follow-through/settle. Browser globe remains a missing-favicon example; official Rovor mark retained. No actual website update is demonstrated.

## Latest: continuous right wrist

Read CARTOON-EVAN-JOINED-WRIST.md. build_joined_wrist.py fits existing hidden-palm wrist width/center to the original forearm, then blends source pixels locally (-36..-12 along wrist axis; fit released over 0..40). Remote forearm and distal palm pixels remain exact. No new generated art or timing. Versioned source hashes/profile in wrist-rig/manifest.json.

JoinedWristArm retains the old forearm grid and extends it across the wrist/palm with the same shoulder/elbow/wrist skin function. Empty unsupported cells are omitted with an interpolation margin; every nontransparent source pixel remains covered. All 489 source-scene poses retain skin-support orientation (minimum signed doubled triangle area 131.75). Distal skin uses the exact hand/index parent. Independent index stays separate. The right palm is now part of a continuous articulated arm skin, not a separate runtime pixel layer; original source parts remain versioned.

JoinedWristSceneBody / render_cartoon_scene.py --joined-wrist uses compact index/current material head; lip-art candidate excluded. export_cartoon_body_psd.py --joined-wrist reopens with seven real pixel layers, mean premultiplied difference .007254/255 before whole-body roll. Not a verified native Moho project. 23 targeted wrist/compact/scene/hand/socket checks pass; tests/export agreement are construction safeguards, not studio quality.

Final review outputs ../../outputs/evan-cartoon-joined-wrist: full branded scene, quarter-speed, same-audio native-pixel before/after wrist review with sample-clock waveform, native skin, final selected stills, PSD and evidence. Only ../cartoon-wrist/scene-final and review-final represent final renders. Full-resolution selected stills inspected; no continuous playback/listening acceptance claimed. All four final films decode cleanly (scene 489/1,956 frames; wrist review 105/420, at 48 fps). Inspected rest/transition/point wrist fragments are closed; source contour/color still needs artist cleanup. Preserve old output studies for comparisons.

## Rejected / limited studies

SculptedContactHead / fv-source-v2 / fv-rig-v2 is a source-space three-part lip/teeth/volume candidate with exact prompt. It has a cleaner held contact but no convincing release improvement; NOT promoted into scene defaults. Initial contact volume/geometry trial bulged and was rejected. Deep index shortening folded the mesh; inward root rotation exposed a cut edge; both rejected. Do not solve missing anatomical drawings by forcing deeper warps.

Details and reproduction: CARTOON-EVAN-CONTACT-ART-V2.md, CARTOON-EVAN-COMPACT-INDEX.md, CARTOON-EVAN-CONTACT-MATERIAL.md and earlier linked docs. Older checkpoints preserved verbatim in PAINTED-EVAN-HISTORY-2026-10-18.md and PAINTED-EVAN-HISTORY-2026-10-18-B.md. Older output folders include evan-cartoon-lip-art, evan-cartoon-compact-hand, evan-cartoon-contact-material, evan-cartoon-narrated-scene and evan-cartoon-rounding.

## Speech evidence

Two-pass PocketSphinx word/phone alignment: 66 words/248 phones, 39-phone catalog, diphthong glides, contacts and silence gating. Reference ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All 18 word-anchor flags already have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json; retain acoustic timing. Exact phone boundaries remain UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Current wrist work leaves annotations/planner weights/recording unchanged.

## Next concrete work / limits

1. Design a softer palm/neighbor-finger pose and clean wrist/knuckle source linework. Keep the continuous wrist skin and independent index attachment; do not restore mismatched cut edges.
2. Improve full lower-mouth contours and designed contact-to-vowel/FV/L tongue construction. Prefer artist-designed anatomical correspondence over more generated full-head variants. Preserve selected proportions.
3. Critically review acting rhythm, then clean shoulder construction. Legs remain static; no eye/blink rig exists behind glasses. A human character artist/animator is still needed for final anatomy/performance approval. CPU raster rendering slows iteration; hardware cannot supply missing drawings. Full polished milestone remains incomplete.

## Runtime

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for render/test batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, user deliverables in outputs/. Inspect alpha art over a solid backdrop; hidden RGB can mislead. No unattended Moho actions.
