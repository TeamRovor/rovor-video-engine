# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; painted-realistic direction is superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photo supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No geometric mouth stickers, skin patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, origin/feature/evan-v4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Routine decisions are authorized. Notify only meaningful review milestones/failure/completion/required action. Full polished cartoon milestone is NOT complete; disable automation only once it actually is ready for review.

## Latest: geometric tooth occlusion candidate

Read CARTOON-EVAN-TOOTH-OCCLUSION.md. OccludedTeethCartoonHead / --occluded-teeth extends BroadCavity. Current rounded art strength s retracts the sampled tooth target upward by s*max(8,.45*oralRingHeight) native pixels before existing 2x mesh sampling. Existing lip/interior matte then covers the teeth. Bypass the old RoundedArt clip fade and set the final rounded-phone tooth factor to 1, avoiding two overlapping opacity fades. Shared aperture/FV fades remain. This is authored 2D relative occlusion, NOT measured jaw depth/anatomy or new phonetic alignment. No new artwork/source pixel changes.

Default teeth-surface and rounded-visibility hooks retain original behavior in older layered/material/lingual modes. Three actual-time Broad baseline frames (2.69,3.0833333333333335,4.6666667 s) remain pixel exact after extraction. 28 targeted checks pass (6 new +22 prior), including all nine exact pure visemes, opaque material retention, fully rounded hiding, local change and valid sampled surfaces. Cavity/tongue controls, jaw/face target geometry, recording, planner, annotations, brows/body and defaults remain unchanged. Tooth target geometry intentionally changes.

Audit: all 489 jaw/face targets remain exact; 77 active-rounded samples, with 13 within 1e-9 of full rounding all having zero tooth alpha after masking. No contour fallback. At frame148 s=.318, retraction4.5328 px leaves an alpha255 core at the lip edge instead of the old .53385 rounded opacity factor. At149 retraction13.4187 px leaves only .0001314/255 residual alpha; at150 zero. These are control/coverage facts, not artistic or anatomical validation.

Review ../../outputs/evan-cartoon-tooth-occlusion: same-audio native-head comparison and full branded integration through “little globe … your logo”/settle, source2.5–5.0 s; normal/quarter120/480 frames at48fps (2.5/10s); all four final films decode cleanly. Selected native transition frames147–149 show a thin white edge being covered, with preceding teeth retained. The two-frame release needs motion review; source tooth band still thin/mechanical and shallow contacts unfinished. Keep OPTIONAL; no default promotion or polished/studio claim. No continuous playback/listening acceptance. Source PSDs/provenance unchanged.

## Existing artwork and rig

Prior broad candidate: separate cavity/rim/matte removes painted red floor; canonical C affine fit [195,316,281,361], source/prompt/hash/generation-chain in broad-source-v1 / broad-rig-v1. Source retains gradients despite prompt. Two-layer C-space PSD error .0004806/255. Prior diagnostic removes only upper teeth at frame148 and grey strip disappears; old rounded factors .6820×.7827=.53385 before source alpha/matte. See CARTOON-EVAN-BROAD-CAVITY-ART.md. Broad mode remains baseline.

Prior lighter O: separate cavity/rim/matte, no peach lip band or baked red floor; canonical E fit [211,320,240,366], light-lip-source-v1 / light-lip-rig-v1. Flattening edit did not fully remove gradients. Two-layer PSD error .0003315/255. See CARTOON-EVAN-LIGHTER-LIP-ART.md. These source-space plates are NOT full/native Moho rigs; manifests animationReady=false.

Head: separate skin/cavity/teeth/tongue floor+blade/closed lips/FV, authored brows, anchored cheek skin, bounded sampled head surfaces. ±62.5ms width lead/release and 83.3ms binomial geometry easing preserve original current contact identity. Optional radial outer-contour correspondence mixes broad/round materials after remapping their drawn silhouettes; not inner-lip anatomical registration. Jaw aperture/chin still share a geometry vector. Existing H already survives energy attenuation (only C/D/E/F attenuated); H is shared L/TH/DH and does not resolve distinct dental or dark/coda L. Earlier sculpted FV/contact candidate rejected for poor release; not promoted. Details in CARTOON-EVAN-CONTOUR-CORRESPONDENCE.md, -ANCHORED-SKIN.md, -BOUNDED-SURFACES.md, -SEPARATED-JAW.md, -LINGUAL-STUDY.md.

Body: separate neck under collar, articulated arm/wrist chains, continuous forearm/wrist/palm skin and independent three-phalange index sharing distal hand parent. Seven actual runtime/PSD layers. Compact index rest retains70% curl/full point exact. Thumb/three neighbors share a drawing and rest remains clenched. Static legs, missing eye/blink controls, wrist/shoulder linework remain. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene:0–10.1875s through favicon/pause with two word-anchored gestures, anticipation/holds/follow-through/settle, official mark and missing-favicon browser-globe example. No actual website update demonstrated. Older full films in evan-cartoon-joined-wrist; focused comparisons in successive output folders.

## Speech evidence

Two-pass PocketSphinx alignment:66words/248phones,39-phone catalog, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged word anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timing until evidence warrants correction. This pass changes no recording, weights or annotation.

## Next concrete work / limits

1. Review tooth entry/release cadence in normal/slow shots; refine the authored occlusion if a pop remains, retaining contact/tongue timing. Then design shallow B/FV contact/release and clean tooth-band anatomy. Do not regenerate another cavity or full head as a shortcut.
2. Distinct L/dental tongue poses and independent chin/jaw under lip seals; retain exact current contacts. Source drawing/inbetweens and a human character artist/animator are needed for final anatomy/performance approval.
3. Softer palm/neighbor fingers, wrist/shoulder linework and expressive eyes/acting. CPU raster warping/source pixels constrain iteration/detail; more output pixels cannot supply drawings. Stop expanding scope and disable automation only when the agreed polished milestone is actually ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, deliverables in outputs/. Composite alpha art over a solid backdrop; hidden RGB misleads.

Previous checkpoint archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-B.md; -2026-10-19.md and earlier -2026-10-18.md/-B.md/-C.md retained. Read specific review docs for details; do not restore superseded defaults.
