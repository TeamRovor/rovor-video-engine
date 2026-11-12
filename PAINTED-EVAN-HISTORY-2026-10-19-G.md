# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; painted-realistic direction is superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photo supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No geometric mouth stickers, skin patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, origin/feature/evan-v4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Routine decisions are authorized. Notify only meaningful review milestones/failure/completion/required action. Full polished cartoon milestone is NOT complete; disable automation only once it actually is ready for review.

## Latest: rooted tongue floor + complete reference (optional)

Read CARTOON-EVAN-ROOTED-FLOOR.md. RootedFloorCartoonHead / --rooted-floor extends Duration. Reuse actual blade/root-floor parts; bladeY=.12+.88*ease(H), X=.8+.2*H, rooted at source(237,354). Floor composites OVER blade; existing lip/interior matte and upper teeth cover the tongue. Ordinary vowel stem retracts, raised tip retained. H still shared L/TH/DH, not separate dental anatomy. Source PNG hashes unchanged; no imagegen/whole-face patch/timing/jaw/body changes this pass.

New profile uses max4 inverse-mesh fields keyed by all source/target points/dtypes/shapes/scale; dynamic pixels always sampled anew. Default warp split into identical map/sample helpers, uncached by default. Duration golden129/145/416 and cached variants pixel exact.13 checks pass (8new+5duration), including root/retraction/tip retention, exact X/A/G, lip/teeth occlusion, dynamic-image separation/invalidation/eviction and pure cache controls. All489tongue rows valid, no dental/FV/rounded fallback. Cache2507hits/1660misses, max4entries. Metrics are pre-lip/material gates, not visible anatomy/quality.

outputs/evan-cartoon-rooted-floor-full has COMPLETE0–10.1875s reference:489normal frames/original voice,1956muted quarter-speed frames at48fps,1280x720. Both films and normal audio decode cleanly. Native512px comparison frames145/147/150/416/434 and whole scene0/145/260/416/480 inspected at full resolution. Cleaner ordinary vowels/rounded floor, contact tip remains. Two editable source-H-space PSDs (blade then floor) reopened; before lip masking, NOT full-head/native Moho rigs. Local mean compositing errors lifted .208878/255, low .025950/255. Exact script excerpt and code/plan/source hashes saved with audits.

Rendering uses CPU on local8GiB/8logical-CPU machine. Sampled workers118–148MiB RSS; duplicate incomplete baseline render stopped to prioritize revised film (partial baseline frames retained). Temporary idle-sleep holds ended with export. Do NOT restart completed renders or assume partial duration-frames is a complete baseline movie.

Current visual limits: HsharedL/TH/DH, heavy lips/corner spurs/plain tooth strip/independent chin, two point accents and mostly fixed palm/neighbor fingers/legs/eyes. Duration undershoot still needs stress/prosody review. No continuous playback/listening or studio-quality acceptance. animationReady:false/default unchanged; full polished milestone incomplete, automation ACTIVE. Prior stable checkpoint archived PAINTED-EVAN-HISTORY-2026-10-19-F.md.

## Retained systems

Head: bounded premultiplied sampling, anchored cheeks, eased shared jaw/chin geometry, optional broad/light rounded cavity/rim/matte and separate cavity/tongue/teeth controls. L/TH/DH still share H, independent chin and eyes remain unfinished. See prior checkpoint and relevant head-study docs.

Body: separate neck under collar, articulated arm/wrist chains, continuous forearm/wrist/palm skin and independent three-phalange index sharing distal hand parent. Seven actual runtime/PSD layers. Compact index rest retains70% curl/full point exact. Thumb/three neighbors share a drawing and rest remains clenched. Static legs, missing eye/blink controls, wrist/shoulder linework remain. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene:0–10.1875s through favicon/pause with two word-anchored gestures, anticipation/holds/follow-through/settle, official mark and missing-favicon browser-globe example. No actual website update demonstrated. Older full films in evan-cartoon-joined-wrist; focused comparisons in successive output folders.

## Speech evidence

Two-pass PocketSphinx alignment:66words/248phones,39-phone catalog, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged word anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timing until evidence warrants correction. This pass changes no recording, weights or annotation.

## Next concrete work / limits

1. Separate L versus dental TH/DH tongue shapes and improve inner lower-lip aperture using consistent source drawings. Use full-reference normal/slow films to target visible defects; review short stressed accents against original voice. Preserve phonetic/material identity and avoid whole-head regeneration. Current ordinary-vowel floor now works without new source art.
2. Distinct L/dental tongue poses and independent chin/jaw under lip seals; retain exact current contacts. Source drawing/inbetweens and a human character artist/animator are needed for final anatomy/performance approval.
3. Softer palm/neighbor fingers, wrist/shoulder linework and expressive eyes/acting. CPU raster warping/source pixels constrain iteration/detail; more output pixels cannot supply drawings. Stop expanding scope and disable automation only when the agreed polished milestone is actually ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for batches. For long unattended local renders, use a temporary idle-sleep hold scoped to the renderer/encoder PID, ending with that process; allow display sleep. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, deliverables in outputs/. Composite alpha art over a solid backdrop; hidden RGB misleads.

Previous checkpoints archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-F.md, -E.md, -D.md, -C.md and -B.md; -2026-10-19.md and earlier -2026-10-18.md/-B.md/-C.md retained. Read specific review docs for details; do not restore superseded defaults.
