# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON; painted-realistic direction is superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photo supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No geometric mouth stickers, skin patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, origin/feature/evan-v4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Routine decisions are authorized. Notify only meaningful review milestones/failure/completion/required action. Full polished cartoon milestone is NOT complete; disable automation only once it actually is ready for review.

## Latest: duration-sensitive jaw / independent contact incisors (optional)

Read CARTOON-EVAN-DURATION-JAW.md. DurationCartoonHead / --duration-jaw extends DentalFVCartoonHead / CorrespondentFV. Short C/D OPEN VOWELS transfer geometry mass toward modest B by .45+.55*ease((duration-.08)/.14), using the planner's onset/release envelope. Existing material/identity/audio-energy weights, A/G contacts, X rest, phone timing and rounded identities remain. Jaw/chin geometry intentionally changes, still shared. This is authored undershoot, not biomechanics/rate/jerk guarantee. Strong short accents may be weakened; performance/prosody review needed.

DentalFV gives the actual fv-rig-v3 incisor component a uniform-thickness child, translated by alpha-weighted X centroid/10%-mass upper-edge difference. Source-support aperture (+1px full margin, falls to0 at distance2) follows lip field and clips teeth over generated underpaint. This is the COMPONENT footprint/guard, not an anatomically drawn lower-lip inner edge or hidden tooth reconstruction. Isolated tooth-only visual difference is subtle and actual matte coverage changes modest. Teeth still mix with vowel materials. No new artwork/source pixel edits/imagegen. Default compositor hook exact at414/422 after extraction.

13 targeted checks pass (9new+4existing), including all9 pure-pose API controls exact, contact/rest/normalization, long-vowel/fallback, anchor translation, source support, synthetic occlusion without uniform material fading and empty-guide fallback. 489scene samples:168geometry apertures change, contact-channel delta0. All34 mixed contacts valid, no dental/FV/rounded fallback. “Favicon” peak aperture44.52→28.20px; max frame step18.49→9.03, second difference24.31→13.25. First489frames max step18.49→9.76. Earlier phrase jaw curve unchanged. These are geometry diagnostics, not rendered-boundary/perceived-smoothness proof.

outputs/evan-cartoon-duration-jaw: main native512px comparison +Rovor integration at8.375–9.375s; earlier “instead of your logo” comparison187/48–235/48s. Each48normal/192muted-quarter frames at48fps; all6films decode cleanly, main/early18/7 dental samples no fallback. Original audio/plan hashes unchanged. Audio-Phone-Jaw.png plots original waveform, stored energy and geometry with unverified source phone boundaries. At416 enormous short-vowel pose visibly moderated; tooth-only change marginal. Heavy lip/corner spurs/plain tooth band/worm-like shared tongue remain. No continuous playback/listening acceptance; animationReady:false/default unchanged, full milestone incomplete.

Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-19-E.md. Shared outer-envelope correspondence and older tooth retraction/source plates remain optional. Do not call either source artwork or scalar motion diagnostics studio quality.

## Retained systems

Head: bounded premultiplied sampling, anchored cheeks, eased shared jaw/chin geometry, optional broad/light rounded cavity/rim/matte and separate cavity/tongue/teeth controls. L/TH/DH still share H, independent chin and eyes remain unfinished. See prior checkpoint and relevant head-study docs.

Body: separate neck under collar, articulated arm/wrist chains, continuous forearm/wrist/palm skin and independent three-phalange index sharing distal hand parent. Seven actual runtime/PSD layers. Compact index rest retains70% curl/full point exact. Thumb/three neighbors share a drawing and rest remains clenched. Static legs, missing eye/blink controls, wrist/shoulder linework remain. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene:0–10.1875s through favicon/pause with two word-anchored gestures, anticipation/holds/follow-through/settle, official mark and missing-favicon browser-globe example. No actual website update demonstrated. Older full films in evan-cartoon-joined-wrist; focused comparisons in successive output folders.

## Speech evidence

Two-pass PocketSphinx alignment:66words/248phones,39-phone catalog, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged word anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timing until evidence warrants correction. This pass changes no recording, weights or annotation.

## Next concrete work / limits

1. Review duration controls over the full reference acting shot, especially short stressed accents and earlier F/V. Preserve exact phone timing/material identity. Then replace the awkward shared tongue drawing and create an artist-faithful inner lower-lip aperture; current component-support matte is not final anatomy. Retain pure/default modes and do not regenerate a whole head to hide defects.
2. Distinct L/dental tongue poses and independent chin/jaw under lip seals; retain exact current contacts. Source drawing/inbetweens and a human character artist/animator are needed for final anatomy/performance approval.
3. Softer palm/neighbor fingers, wrist/shoulder linework and expressive eyes/acting. CPU raster warping/source pixels constrain iteration/detail; more output pixels cannot supply drawings. Stop expanding scope and disable automation only when the agreed polished milestone is actually ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, deliverables in outputs/. Composite alpha art over a solid backdrop; hidden RGB misleads.

Previous checkpoints archived verbatim PAINTED-EVAN-HISTORY-2026-10-19-E.md, -D.md, -C.md and -B.md; -2026-10-19.md and earlier -2026-10-18.md/-B.md/-C.md retained. Read specific review docs for details; do not restore superseded defaults.
