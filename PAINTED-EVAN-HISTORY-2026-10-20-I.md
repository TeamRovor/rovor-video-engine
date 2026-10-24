# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photograph supplies loose identity only; realistic painted direction superseded. Preserve hair/glasses/navy shirt/black tie and official Rovor mark. No photographic facial crops, geometric mouth stickers or flattened whole-character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work authorized. Never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful milestones/failure/completion/required action only; disable once the agreed polished milestone is actually ready. Routine decisions need no question.

## Latest: coordinated full-face mouth construction, SOURCE ONLY

Read CARTOON-EVAN-MOUTH-CONSTRUCTION.md. Built-in image_gen made two coordinated seal/release/rounded full-head construction sheets in mouth-construction-v1/source, from actual rig738/741/742 triptych plus selected design sheet. V1 rejected: hooked corner and broad toothed release. V2 has softer closed ends and narrow dark release without teeth. Exact prompts, hashes, original alpha and canonical working-reference-738.png retained. This is coordinated source drawing work, NOT a new runtime mouth profile.

New audit_cartoon_construction.py extracts alpha components and fits ONLY upper face to canonical512px reference (mask x90–419/y80–294). ECC .990906/.991562/.991759; upper RGB errors7.29/7.05/6.96 of255. Diagnostic alignment passes; registrationReady/animationReady remain FALSE because separated skin/seal/lower-inner-lip/cavity/teeth/tongue/jaw planes and matched correspondences are absent. High ECC is not anatomy, topology, lip sync or rig acceptance. No full-head swaps/morph animation. Original source files untouched; affine diagnostic copies resample associated color.

outputs/evan-cartoon-mouth-construction: native aligned512px references, fullsourcev2, exact Prompt-Set/Provenance, Artist-Construction-Reference.psd (FOUR FULL-HEAD reference layers, only Seal visible; NOT expanded mouth rig/nativeMoho). PSD reload error .000083/255. Real-voice Source-Construction-Review normal60/slow240frames at2160x720/48fps; source714–773 (14.875–16.125s). LEFT is unchanged working RoundedDuration head; THREE right heads STATIC source references, clearly labeled. No candidate lip-sync or improved-animation claim. Both films fully decode; original WAV/decoded AAC20000samples16k from238000–257999 inclusive, full audio helper used. Oral fallback counters0. Two diagnostic tests pass; no art acceptance implied.

Raw v1/v2, aligned1600px triptych, native Release512 on opaque backdrop and review738 board inspected (2160px board display resized to2048; component views native). Red/yellow raw-view neck speckles are near-transparent RGB: measured red pixels maxalpha1/255, vanish on proper backdrop; do NOT misdiagnose/colour-key them away. Softer seal/narrow release useful as source direction, but they still do not supply coordinated independent jaw/interior layers. No independent listening/continuous-playback approval. Exact18flagged timings remain unverified. No pending renders; no runtime/default/source rig changes. Full polished milestone incomplete, automation ACTIVE.

Prior complete narrated thought/export fix: read FINISHED-THOUGHT doc/history G/H. Optional Finished scene at outputs/evan-cartoon-finished-thought224normal/896slow frames, original74667samples. Official brand reveal/second gesture; unchanged mouth art. narrated_export helper avoids -frames:v/-shortest truncation in audio mux; fractional224frame integration check passed. Preserve that fix. No further staging scope until actual mouth layers are constructed.

## Retained systems and rejected work

Relaxed hand: read RELAXED-HAND doc. Built-in imagegen v1 counting pose rejected, v2 registered with alpha retained; right-skin is actual continuous forearm/hand layer. All five digits share wrist; no individual finger animation/pose switching. Forearm-axis wrist weights fixed old Y-only foldover on thumb. Default posed_vertices hook previously matched scene684/748 JPEGs byte exact. Six actual posed PSD body planes verified (.00717/255 mean), not native Moho skeleton or expanded face rig. Source hashes/prompts/history retained in relaxed-hand-v1 and outputs/evan-cartoon-relaxed-hand.

Detail acting: contiguous super/small/detail script43/44/45 anchors authored preparation/hold/settle with elbow/wrist/index/head offsets. Read DETAIL-ACTING doc; outputs/evan-cartoon-detail-acting has original normal/slow and comparison. Earlier pointing accents remain for globe/up here and favicon. Legs static; eyes/blinks unrigged. Current relaxed profile reuses same acting, not emotion inference.

RoundedDuration: AO/E-only authored excursion floor75% for<=80ms, unchanged>=220ms. Original X/corners/rounding, independent chin track and contact weights preserved. Existing60/60/190ms AO labels in small/more/all remain unverified; no retiming. Read ROUNDED-DURATION doc. UniformSeal artwork remains UNAPPROVED; isolated seam glyphs did not fix compound release. Do not promote it or repeat isolated seam generation.

IndependentChin:9tap/48Hz control of three existing skin anchors45/46/47, not a redrawn mandible. Earlier shared-target bug suspicion was disproved; source targets already separate. DrawnDental provides registered TH/DH source and floor/tooth occlusion, old L retained. Previous compressed-L blade rejected. RootedFloor/cache full0–10.1875s489normal/1956slow reference completed; do not re-render or mistake partial duration frames for full baseline. Associated docs/outputs and history retain evidence.

Speech:66 words/248 phones/39 ARPABET; two-pass acoustic alignment, coarticulation/diphthongs/contact/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18 flagged anchors have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json; exact boundaries UNVERIFIED. Coverage is not accuracy. Preserve timings until evidence warrants correction.

## Next concrete work

1. From coordinated v2 context, produce a compatible CLEAN skin plate and separate seal/lip rim, lower inner lip, cavity and jaw surfaces. Define actual matched lip-corner/inner-lip/jaw correspondences. Apply imagegen skill for generated source; no isolated seam glyphs or full-head swaps. Current sheets/PSD are references, not registered components. Do not promote them just because upper-face ECC passes.
2. Test source correspondence, contact sealing, interior occlusion and jaw volume under actual voice, native normal/slow, before any optional runtime profile. Human character artist/animator redraw and review remain needed for final anatomy/performance. Faster hardware cannot supply missing drawings.
3. Preserve complete decoded narration with narrated_export, retain18flagged timing uncertainty and all release safeguards. Full polished milestone incomplete.

## Runtime and history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. cv2.setNumThreads(1). Local8GiB/8logical CPUs, CPU raster rendering. Temporary caffeinate scoped to long renderer/encoder, display sleep allowed. No scipy: FFT evidence uses numpy/matplotlib with MPLCONFIGDIR in work/. Recording sibling referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav mono PCM16/16k; FFmpeg sibling work/media-tools/ffmpeg. Scratch work/cartoon-mouth-construction, work/cartoon-finished-thought and work/cartoon-relaxed-hand and earlier work/cartoon-detail-acting/rounded-duration/lip-seal retained. User deliverables outputs/.

Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-20-H.md; -G/-F/-E/-D/-C/-B and prior history retain details. No pending renders/exports. Continue from actual branch state.
