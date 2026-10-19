# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; painted-realistic direction is superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photo supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No geometric mouth stickers, skin patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, origin/feature/evan-v4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Routine decisions are authorized. Notify only meaningful review milestones/failure/completion/required action. Full polished cartoon milestone is NOT complete; disable automation only once it actually is ready for review.

## Latest: shared F/V release silhouette (optional)

Read CARTOON-EVAN-FV-CORRESPONDENCE.md. CorrespondentFVCartoonHead / --correspondent-fv extends PlanarFV. Reuses existing contour_maps: largest50%-alpha contours at4x,256 radial rays, weighted center/envelope. Remap separate cavity/teeth/tongue/closed lips with the vowel field and F/V construction with contact field before mixing. No source art/timing/annotation/face geometry changes. This is drawn-envelope correspondence, not anatomical topology. Source/registered fv-rig-v3 layers/PSD/prompts remain recorded in CARTOON-EVAN-PLANAR-FV.md.

New oral blend is restricted to the original largest opaque oral bounds+3px antialias margin; previous blend exact outside. Initial locality test caught four one-step skin-pixel differences from resampled alpha dust; guard added, final tests/renders rerun. Ten targeted checks pass (4 new +6 prior planar tests), including all9 pure visemes exact, local change, reduced silhouette mismatch, valid surfaces and degenerate fallback. Across489 targets jaw/face delta0. All34 mixed-contact samples register, no FV/rounded fallback;50%-alpha silhouette disagreement sum29419→1919pixels (414:779→48;422:570→49). Metric is outer contour only, not phonetic/artistic/temporal acceptance.

outputs/evan-cartoon-fv-correspondence contains native-head before/after and branded normal/quarter-speed clips, source8.375–9.375s (“a favicon” through start of pause),48/192frames at48fps, all4final films decode cleanly,18review mixed samples no fallback. Full-resolution release414/422 shows reduced obvious double outer edge. Contact still slightly smiling/heavy-lipped; corner spurs, thin tooth strip and internal colour interpolation remain mechanical. No continuous playback/listening acceptance. animationReady:false, default unchanged; full milestone incomplete.

Previous planar source/placement candidate and geometric tooth occlusion remain optional. Earlier checkpoint archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-D.md. Do not regenerate another cavity/full head to hide remaining anatomy.

## Retained systems

Head: bounded premultiplied sampling, anchored cheeks, eased shared jaw/chin geometry, optional broad/light rounded cavity/rim/matte and separate cavity/tongue/teeth controls. L/TH/DH still share H, independent chin and eyes remain unfinished. See prior checkpoint and relevant head-study docs.

Body: separate neck under collar, articulated arm/wrist chains, continuous forearm/wrist/palm skin and independent three-phalange index sharing distal hand parent. Seven actual runtime/PSD layers. Compact index rest retains70% curl/full point exact. Thumb/three neighbors share a drawing and rest remains clenched. Static legs, missing eye/blink controls, wrist/shoulder linework remain. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene:0–10.1875s through favicon/pause with two word-anchored gestures, anticipation/holds/follow-through/settle, official mark and missing-favicon browser-globe example. No actual website update demonstrated. Older full films in evan-cartoon-joined-wrist; focused comparisons in successive output folders.

## Speech evidence

Two-pass PocketSphinx alignment:66words/248phones,39-phone catalog, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged word anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timing until evidence warrants correction. This pass changes no recording, weights or annotation.

## Next concrete work / limits

1. Add independent incisor/lower-lip contact occlusion through F/V release; a shared outer envelope does not solve internal contact anatomy. Use414/422 plus high-contact411/420, retain exact pure/non-contact controls and acoustic weights. Assess early F/V regions too. Keep optional until normal-speed performance is acceptable, then assess B seals/tooth-band anatomy.
2. Distinct L/dental tongue poses and independent chin/jaw under lip seals; retain exact current contacts. Source drawing/inbetweens and a human character artist/animator are needed for final anatomy/performance approval.
3. Softer palm/neighbor fingers, wrist/shoulder linework and expressive eyes/acting. CPU raster warping/source pixels constrain iteration/detail; more output pixels cannot supply drawings. Stop expanding scope and disable automation only when the agreed polished milestone is actually ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, deliverables in outputs/. Composite alpha art over a solid backdrop; hidden RGB misleads.

Previous checkpoints archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-D.md, -C.md and -B.md; -2026-10-19.md and earlier -2026-10-18.md/-B.md/-C.md retained. Read specific review docs for details; do not restore superseded defaults.
