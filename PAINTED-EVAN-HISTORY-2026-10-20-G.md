# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photograph supplies loose identity only; realistic painted direction superseded. Preserve hair/glasses/navy shirt/black tie and official Rovor mark. No photographic facial crops, geometric mouth stickers or flattened whole-character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work authorized. Never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful milestones/failure/completion/required action only; disable once the agreed polished milestone is actually ready. Routine decisions need no question.

## Latest: relaxed hand source and actual wrist defect fix

Read CARTOON-EVAN-RELAXED-HAND.md. Optional RelaxedCartoonSceneBody / --relaxed-hand extends Detail -> RoundedDuration. Built-in image_gen made two transparent source plates in relaxed-hand-v1/source with exact Prompt-Set/Provenance/ref hashes. V1 counting silhouette rejected; v2 opens ring/little into an open cascade. Original generated alpha preserved. Manually inspected wrist(531,500) -> (810,762), .16 scale/15deg. Alpha cross-section fit releases by s=40; original proximal arm exact through s<=-36, blend -36..-12 along normalized(61,137). Registered right-skin.png is an actual working continuous forearm/hand layer, not the source plate.

Old vertical-Y wrist influence folded a triangle on the wider thumb at source767 (doubled area about -320.6). RelaxedWristArm now uses forearm-axis wrist distance, smooth -30..30. Distal vertices have exact hierarchical wrist parent. ArmMesh.posed_vertices hook delegates unchanged by default: previous scene JPEGs684/748 byte exact. Only this optional arm uses new weights. Remove old index from composition. All five digits share ONE drawn pose: no independent finger controls, point/open transition, sprite switch or finger dissolve.

outputs/evan-cartoon-relaxed-hand: continuous source684–827 (14.25–17.25s), 144 normal original-voice / 576 muted quarter-speed frames at1280x720/48fps. Same full interval comparison LEFT old point / RIGHT open hand at2560x720,144/576 frames. All four films fully decode clean; both normal films decode48000 PCM16 samples at16kHz. Four tests pass including1059 reference-control mesh scan.144 rendered arm audits positive (min doubled areas left535.8228/right135.3515); all captured oral fallback counters zero. Same acting/scene/mouth/acoustic timings as prior detail shot.

Source v1/v2, selected concept, native wrist registration/posed767, final native scene767/827 and encoded767 inspected. New open silhouette is friendlier for explanation; palm perspective, thin ink/knuckle creases and wrist linework remain limited. No independent listening/continuous-playback acceptance. Six actual posed pixel planes exported/reopened as Working-Body-Planes.psd; mean premultiplied difference .0071694/255. Before body roll; posed head is composite, right hand part of arm skin. NOT native Moho bones or expanded face rig. No pending renders; temporary sleep holds ended.

## Retained systems and rejected work

Detail acting: contiguous super/small/detail script43/44/45 anchors authored preparation/hold/settle with elbow/wrist/index/head offsets. Read DETAIL-ACTING doc; outputs/evan-cartoon-detail-acting has original normal/slow and comparison. Earlier pointing accents remain for globe/up here and favicon. Legs static; eyes/blinks unrigged. Current relaxed profile reuses same acting, not emotion inference.

RoundedDuration: AO/E-only authored excursion floor75% for<=80ms, unchanged>=220ms. Original X/corners/rounding, independent chin track and contact weights preserved. Existing60/60/190ms AO labels in small/more/all remain unverified; no retiming. Read ROUNDED-DURATION doc. UniformSeal artwork remains UNAPPROVED; isolated seam glyphs did not fix compound release. Do not promote it or repeat isolated seam generation.

IndependentChin:9tap/48Hz control of three existing skin anchors45/46/47, not a redrawn mandible. Earlier shared-target bug suspicion was disproved; source targets already separate. DrawnDental provides registered TH/DH source and floor/tooth occlusion, old L retained. Previous compressed-L blade rejected. RootedFloor/cache full0–10.1875s489normal/1956slow reference completed; do not re-render or mistake partial duration frames for full baseline. Associated docs/outputs and history retain evidence.

Speech:66 words/248 phones/39 ARPABET; two-pass acoustic alignment, coarticulation/diphthongs/contact/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json; exact boundaries UNVERIFIED. Coverage is not accuracy. Preserve timings until evidence warrants correction.

## Next concrete work

1. Review a longer coherent narrated passage with the open hand and deliberate staging, preserving chosen cartoon identity. Add useful articulation only with compatible hidden surfaces/inbetweens; do not dissolve or instantly switch point/open fingers and call it fluid motion.
2. Coordinate artist-drawn lower-inner-lip/seal/open-lip/jaw inbetweens and improve hand/shoulder linework. No indefinite isolated mouth-glyph/control microtuning. Human character artist/animator needed for final anatomy and performance review; hardware cannot supply missing drawings.
3. Continue actual-voice normal/slow full-scene review; retain timing uncertainty and all release safeguards. Full polished milestone incomplete.

## Runtime and history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. cv2.setNumThreads(1). Local8GiB/8logical CPUs, CPU raster rendering. Temporary caffeinate scoped to long renderer/encoder, display sleep allowed. No scipy: FFT evidence uses numpy/matplotlib with MPLCONFIGDIR in work/. Recording sibling referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav mono PCM16/16k; FFmpeg sibling work/media-tools/ffmpeg. Scratch work/cartoon-relaxed-hand and earlier work/cartoon-detail-acting/rounded-duration/lip-seal retained. User deliverables outputs/.

Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-20-F.md; -E/-D/-C/-B and prior history retain details. No pending renders/exports. Continue from actual branch state.
