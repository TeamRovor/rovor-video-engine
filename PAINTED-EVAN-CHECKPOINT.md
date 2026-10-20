# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photograph supplies loose identity only; realistic painted direction superseded. Preserve hair/glasses/navy shirt/black tie and official Rovor mark. No photographic facial crops, geometric mouth stickers or flattened whole-character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work authorized. Never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful milestones/failure/completion/required action only; disable once the agreed polished milestone is actually ready. Routine decisions need no question.

## Latest: complete narrated thought and export tail fix

Read CARTOON-EVAN-FINISHED-THOUGHT.md. Optional FinishedCartoonSceneBody/FinishedStage reuses relaxed hand, detail accent and existing mouth profile. Contiguous whole/website/feel/way/more/finished script50–55 anchors a350ms browser reveal at website17.18s and second open-palm/head/brow accent through “way more finished.” Prior stage incorrectly kept missing-globe question during payoff and body went idle. Actual official Rovor mark now replaces globe; initial overlap preview rejected, sequential non-overlapping fades used. Copy changes once mark legible. Existing default/profiles and character art unchanged. Script-specific authored shot, not generic automatic directing or emotion inference.

Source render696–935 (14.5–19.5s),240frames audits positive. Export696–919 (14.5–19.1667s),224normal/896muted quarter-speedframes at1280x720/48fps: full “Super small detail, but it makes the whole website feel way more finished.” Waveform/FFT review selected quiet cut before following low-level sound; no retiming/fades. Exact boundaries/listening remain unverified. Extra16source frames of settle remain in scratch, outside delivered cut. Audio samples232000–306666 inclusive,74667mono PCM16 samples16k.

Export check caught real truncation: one-command -frames:v mux produced73728decoded samples (58.7ms missing). New narrated_export.mux_complete_audio muxes full cropped WAV after finite silent video encoding, sets movie timebase to source rate, verifies sample count, atomically replaces output. One real FFmpeg integration regression passes (224frames/240input images/74667samples). Final film fully decodes224frames AND74667samples; slow896frames. AAC lossy, original cropped WAV verbatim. Do not reintroduce -frames:v/-shortest in audio mux. Six staging tests pass including1059reference arm controls and no globe/mark ghosting. All240rendered meshes positive; minimum arm doubled areas left494.6158/right135.3515; captured oral fallbacks0.

outputs/evan-cartoon-finished-thought includes normal/slow films, original WAV, source900 old/new payoff stills, encoded payoff, native reveal834/846, Voice-Staging-Review1920x1080, audit/review/evidence. First-accent frame748 left640px byte exact to prior relaxed shot. Native old/new900, final834/900, encoded900 and plot inspected. Clearer narrative payoff; frontal head, one drawn hand, static legs and missing coordinated lip/jaw inbetweens remain. No independent listening/continuous-playback approval. No pending renders/exports; sleep holds ended. Full polished milestone NOT ready, automation ACTIVE.

## Retained systems and rejected work

Relaxed hand: read RELAXED-HAND doc. Built-in imagegen v1 counting pose rejected, v2 registered with alpha retained; right-skin is actual continuous forearm/hand layer. All five digits share wrist; no individual finger animation/pose switching. Forearm-axis wrist weights fixed old Y-only foldover on thumb. Default posed_vertices hook previously matched scene684/748 JPEGs byte exact. Six actual posed PSD body planes verified (.00717/255 mean), not native Moho skeleton or expanded face rig. Source hashes/prompts/history retained in relaxed-hand-v1 and outputs/evan-cartoon-relaxed-hand.

Detail acting: contiguous super/small/detail script43/44/45 anchors authored preparation/hold/settle with elbow/wrist/index/head offsets. Read DETAIL-ACTING doc; outputs/evan-cartoon-detail-acting has original normal/slow and comparison. Earlier pointing accents remain for globe/up here and favicon. Legs static; eyes/blinks unrigged. Current relaxed profile reuses same acting, not emotion inference.

RoundedDuration: AO/E-only authored excursion floor75% for<=80ms, unchanged>=220ms. Original X/corners/rounding, independent chin track and contact weights preserved. Existing60/60/190ms AO labels in small/more/all remain unverified; no retiming. Read ROUNDED-DURATION doc. UniformSeal artwork remains UNAPPROVED; isolated seam glyphs did not fix compound release. Do not promote it or repeat isolated seam generation.

IndependentChin:9tap/48Hz control of three existing skin anchors45/46/47, not a redrawn mandible. Earlier shared-target bug suspicion was disproved; source targets already separate. DrawnDental provides registered TH/DH source and floor/tooth occlusion, old L retained. Previous compressed-L blade rejected. RootedFloor/cache full0–10.1875s489normal/1956slow reference completed; do not re-render or mistake partial duration frames for full baseline. Associated docs/outputs and history retain evidence.

Speech:66 words/248 phones/39 ARPABET; two-pass acoustic alignment, coarticulation/diphthongs/contact/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json; exact boundaries UNVERIFIED. Coverage is not accuracy. Preserve timings until evidence warrants correction.

## Next concrete work

1. Move back to coordinated mouth construction: design compatible closed/seal, lower inner lip and open-jaw inbetweens in the chosen cartoon style, preserving full-face context/corners and jaw volume. No more isolated seam glyphs or indefinite minor control tuning; stop expanding staging scope for now. Apply imagegen skill if making source, distinguish source plates from registered working components and compare native normal/slow actual voice before promotion.
2. Improve hand/shoulder ink and compatible hidden surfaces only where actual defects remain. Human character artist/animator needed for final anatomy, coordinated redraws and performance review; hardware cannot supply missing drawings.
3. Preserve full decoded audio with the new export helper, retain18flagged timing uncertainty and all release safeguards. Full polished milestone incomplete.

## Runtime and history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. cv2.setNumThreads(1). Local8GiB/8logical CPUs, CPU raster rendering. Temporary caffeinate scoped to long renderer/encoder, display sleep allowed. No scipy: FFT evidence uses numpy/matplotlib with MPLCONFIGDIR in work/. Recording sibling referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav mono PCM16/16k; FFmpeg sibling work/media-tools/ffmpeg. Scratch work/cartoon-finished-thought and work/cartoon-relaxed-hand and earlier work/cartoon-detail-acting/rounded-duration/lip-seal retained. User deliverables outputs/.

Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-20-G.md; -F/-E/-D/-C/-B and prior history retain details. No pending renders/exports. Continue from actual branch state.
