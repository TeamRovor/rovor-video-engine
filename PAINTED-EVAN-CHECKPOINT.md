# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; painted-realistic direction is superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photo supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No geometric mouth stickers, skin patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, origin/feature/evan-v4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Routine decisions are authorized. Notify only meaningful review milestones/failure/completion/required action. Full polished cartoon milestone is NOT complete; disable automation only once it actually is ready for review.

## Latest: optional shallow F/V source and uniform placement

Read CARTOON-EVAN-PLANAR-FV.md. PlanarFVCartoonHead / --planar-fv extends OccludedTeeth. Built-in imagegen contact-v4 plus generated tooth-hidden underpaint are separated into two actual registered lip-contact/upper-teeth layers (fv-source-v3 / fv-rig-v3), with exact prompts/source hashes/generation graph and reopened two-layer PSD evidence. The raw source plate is not a rig. Uniform corner placement prevents jaw aperture from crushing/inflating contact art; both layers currently share a parent. One shared F/V pose, no calibrated anatomy or independent tooth contact joint. Older/default modes unchanged.

12 targeted checks pass (6 new +6 tooth-occlusion), eight non-G pure controls exact; G intentionally changes. All489 jaw/face targets exact,34 active contact samples; positive uniform matrices (minimum determinant .176753, max uniform error .000001799). No timing/recording/annotation changes. Canonical source reassembly local mean premultiplied error .492607/255; reopened PSD .00007991/255 globally.

outputs/evan-cartoon-planar-fv has native-head before/after and branded normal/quarter-speed shots covering source8.1875–10.1875s,96/384frames at48fps, chosen raw source/hidden underpaint/exact prompt set/PSD/registration/audit. Full-resolution contact411/420 is clearer than the slit but still slightly smiling/heavy-lipped. Transition414/422 exposes DOUBLE LIP CONTOURS from existing contact/vowel alpha blend. Following vowel426 unchanged. Candidate is NOT promoted, animationReady:false. No continuous playback/listening or studio-quality acceptance claimed.

Previous geometric tooth occlusion remains optional and unchanged (CARTOON-EVAN-TOOTH-OCCLUSION.md); separate retraction preserves material until the lip matte hides teeth. Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-19-C.md.

## Retained systems

Head: bounded premultiplied sampling, anchored cheeks, eased shared jaw/chin geometry, optional broad/light rounded cavity/rim/matte and separate cavity/tongue/teeth controls. L/TH/DH still share H, independent chin and eyes remain unfinished. See prior checkpoint and relevant head-study docs.

Body: separate neck under collar, articulated arm/wrist chains, continuous forearm/wrist/palm skin and independent three-phalange index sharing distal hand parent. Seven actual runtime/PSD layers. Compact index rest retains70% curl/full point exact. Thumb/three neighbors share a drawing and rest remains clenched. Static legs, missing eye/blink controls, wrist/shoulder linework remain. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene:0–10.1875s through favicon/pause with two word-anchored gestures, anticipation/holds/follow-through/settle, official mark and missing-favicon browser-globe example. No actual website update demonstrated. Older full films in evan-cartoon-joined-wrist; focused comparisons in successive output folders.

## Speech evidence

Two-pass PocketSphinx alignment:66words/248phones,39-phone catalog, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged word anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timing until evidence warrants correction. This pass changes no recording, weights or annotation.

## Next concrete work / limits

1. Fix mixed F/V-to-vowel double contours at frames414/422 through shared outer-lip correspondence and incisor/lower-lip occlusion. Preserve acoustic timing and exact non-contact controls. Do not promote the new source/placement candidate yet; do not hide it with a full-face patch. Then assess B seals and tooth-band anatomy.
2. Distinct L/dental tongue poses and independent chin/jaw under lip seals; retain exact current contacts. Source drawing/inbetweens and a human character artist/animator are needed for final anatomy/performance approval.
3. Softer palm/neighbor fingers, wrist/shoulder linework and expressive eyes/acting. CPU raster warping/source pixels constrain iteration/detail; more output pixels cannot supply drawings. Stop expanding scope and disable automation only when the agreed polished milestone is actually ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, deliverables in outputs/. Composite alpha art over a solid backdrop; hidden RGB misleads.

Previous checkpoints archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-C.md and -B.md; -2026-10-19.md and earlier -2026-10-18.md/-B.md/-C.md retained. Read specific review docs for details; do not restore superseded defaults.
