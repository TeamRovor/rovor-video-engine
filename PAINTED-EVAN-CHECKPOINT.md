# Evan animation: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; the photograph supplies loose identity cues. Use cartoon-v1/source/design-sheet-v1.png and CARTOON-EVAN-DIRECTION.md. The realistic painted direction is superseded. Preserve tousled hair, sunglasses, navy shirt/black tie and official Rovor branding. Do not replace the selected character with geometric mouth patches or a new full-character sprite.

Checkout work/engine, development/evan-painted-rig. Draft PR #4: https://github.com/TeamRovor/rovor-video-engine/pull/4, based on experiment/moho-native-rig. Commit bounded improvements to development only. Never merge/deploy without explicit approval. Main remains 4e099b5f1a30661c952358f49e1e2d70a5fe2a62; V4 known 27b664b9daa924ff17d3b874264bc4cef7131196. Preserve V3/V4, approved symlinks/updater and native projects. Do not launch/restart/probe Moho unattended after its earlier crash.

Automation develop-evan-painted-animation stays ACTIVE; notify only on meaningful milestone/failure/completion/required action. Make routine decisions autonomously. Disable it only when the complete polished cartoon animation milestone is actually ready for review. That milestone is NOT complete.

## Working rig

All latest work is opt-in. Original classes/defaults remain comparison baselines. Base layered art uses registered head-rig-v2, oral-rig, body-rig, hand-rig, socket-rig, expression-rig, fv-rig and neck-art-rig under evan-character/cartoon-v1.

- LayeredCartoonHead separates skin/cavity/teeth/tongue/lips. ExpressiveCartoonHead adds original independent brows; FVContactHead uses a relaxed separate lip/upper-teeth contact candidate.
- SolidCavityHead fixes the brown neutral/rounded transition by keeping the cavity solid, retaining tilted closure geometry and solid closed ink until the inner opening replaces it. See CARTOON-EVAN-SOLID-CAVITY.md.
- Registered neck/collar art closes the previously observed pale gaps in native 0/+8/-8 tilt checks. Neck is independent from the fixed collar, with a small residual left-jaw fold. Seven-layer PSD is real pixel layers, not a verified Moho bone rig. See CARTOON-EVAN-NECK-ART.md.
- Original open and pointing drawings attach to hierarchical wrists; the new scene adds a separate continuously bent index, while the other digits remain drawn. Underarm bands reduce tabs; shoulder/wrist creases and thin hand linework remain.

## Latest: independent rounded lip width

Read CARTOON-EVAN-ROUNDING-CONTROL.md. RoundedCartoonHead / CartoonRoundedBody / --rounding separates rounded lip width from audio-driven jaw opening. It samples existing acoustic phone shape before energy attenuation, preserves contacts/silence, and uses a shape-only symmetric ±62.5 ms lead/release. This is authored coarticulation, not new boundary measurement. All mouth Y/non-mouth coordinates and 1,059 default weight vectors remain exact. The lip-shape change is confined to oral surfaces; skin retains the original jaw target to prevent a cheek texture artifact caught in full-head review. No new artwork or timing annotations. 108 checks pass; this is not perceptual acceptance.

The first new width control released too sharply; filtering reduces its logo-release peak step from 29.96 to 11.95 source pixels/frame (prior baseline 11.98). This does not establish perceptual smoothness. Quiet OW tails hold a narrower pucker, but lips remain wedge-like/jagged and need cleaner construction. Latest normal/quarter-speed native-head comparison, original waveform, native crops, branded body still, width/jaw plot and full-recording evidence are in ../../outputs/evan-cartoon-rounding. Only scratch ../cartoon-rounding/review-final matches final code; earlier frames/final-frames include superseded experiments. Full-resolution frames were inspected; no continuous movie playback/listening verification claimed.

Earlier review outputs remain under ../../outputs/evan-cartoon-solid-mouth, evan-cartoon-neck-art, evan-cartoon-fv, evan-cartoon-expressions and evan-speech-timing-audit. Historical details and all earlier limitations are preserved in PAINTED-EVAN-HISTORY-2026-10-18.md and their linked docs.

## Speech evidence

Two-pass PocketSphinx forced word/phone alignment, 66 words/248 phones, 39-phone catalog with diphthong glides/contacts/held vowels and silence gating. Reference plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All 18 word-anchor flags already have waveform/spectrogram visual evidence review in evan-engine/reviews/evan-reference-timing-v1.json; retain current acoustic timings. Exact phone boundaries remain UNVERIFIED, with no listening/ground-truth verification. Coverage is not timing accuracy. Current changes leave annotations/cached controls untouched. See SPEECH-TIMING-REVIEW.md and ACOUSTIC-SPEECH-ALIGNMENT.md.

## Latest: longer scene and independent index

Read CARTOON-EVAN-NARRATED-SCENE.md. New CartoonSceneBody / render_cartoon_scene.py integrates the existing current head/neck rig in a 0–10.1875 s scene through favicon and its pause. Two authored word-anchored gestures have drawback, follow-through, held pointing and a pause settle. Browser globe remains a placeholder, highlighted on favicon; official Rovor mark is used. Engineering captions are omitted from the new scene only.

New generated hidden-palm source/prompt is in index-source; registered working palm/index and source hashes in index-rig. First local patch left a notch; final coherent hidden palm below a feathered wrist fixes that visible cut. The original point drawing supplies a separate three-phalange index with continuous skinning. Only the index is articulated; thumb/three curled neighbors remain one drawing. Rest is a loose curled index, not a fully relaxed new hand pose. Range is MCP -10..0 / PIP 0..60 / DIP 0..35; unreviewed ranges are rejected. Sharp initial weights pinched; broad final weights preserve orientation across the shot.

Outputs ../../outputs/evan-cartoon-narrated-scene: normal/quarter-speed films, reopened eight-layer PSD (mean difference .00747/255), native curled/half/point composites, generated hidden-palm source/exact prompt, cue timeline and pause evidence. Original audio/annotations remain unchanged; central pause mouth rest weight is 1. All 18 timing flags retain their visual review and uncertainty. 114 checks pass, not perceptual approval. Full-resolution source/assembled frames inspected; no continuous movie playback/listening verification claimed. Only scratch ../cartoon-index/scene-final matches the final working components; earlier scene-frames and pose experiments are superseded.

## Next concrete work

1. Clean the index root/knuckle/wrist artwork and add a designed softer palm/remaining-finger pose; current thumb/three curls remain rigid and the resting index can read as a hook. Review the whole shot at normal speed for deliberate rhythm before adding incidental motion.
2. Review the muddy narrow lip at 8.79 s locally, then redraw rounded/FV lower-lip and L/tongue anatomy with clean contours; keep generated source plates separate from registered working parts. Preserve selected likeness; reject global proportion changes.
3. Clean shoulder construction; legs remain static and eyes have no blink rig behind glasses. A character artist/animator is still needed for final anatomy/performance. Do not equate tests, frame counts or flatter sprite swaps with studio quality. Full polished milestone remains incomplete; automation stays ACTIVE.

## Runtime

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Set cv2.setNumThreads(1) for render batches. Original mono PCM16 narration: /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav. FFmpeg sibling work/media-tools/ffmpeg. Keep scratch in work/, user deliverables in outputs/. Use solid-background composites when inspecting alpha assets; hidden RGB can mislead raw previews. CPU iteration speed does not fix missing drawings. No unattended Moho activity.
