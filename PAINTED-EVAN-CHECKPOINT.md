# Evan cartoon: current checkpoint

## Direction / safeguards

Entertaining expressive 2D CARTOON; original photo supplies loose identity cues only. Follow CARTOON-EVAN-DIRECTION.md and cartoon-v1/source/design-sheet-v1.png. Preserve hair/glasses/navy shirt/black tie and official branding. Painted-realistic direction is superseded. No geometric mouth patches or flattened character replacement.

Repo work/engine, branch development/evan-painted-rig (historical name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4 based on experiment/moho-native-rig. Commit/push bounded development work only. Never merge/deploy without explicit approval. Preserve main 4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4, approved releases/symlinks/updater and native projects. Do not launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Make routine decisions autonomously. Notify only meaningful review milestones/failure/completion/required action. Disable only when the full polished cartoon milestone is actually ready for review. It is NOT complete.

## Latest: bounded head samples (renderer QA)

Read CARTOON-EVAN-BOUNDED-SURFACES.md. BoundedCartoonHead / --bounded-head enables constrain_surface hooks on sampled head skin/oral/FV/tongue layers and pre-composite tongue-affine samples. Negative coverage/RGB lobes are removed; alpha above 255 is rescaled with RGB to preserve positive-alpha straight colour, then RGB is limited to [0, alpha]. Valid finite samples stay exact. Body and brow sampling are unchanged; this is not global renderer enforcement or a linear-light conversion. Source art, targets, timing and phoneme weights are unchanged.

51 affected checks pass (six new plus prior head regressions). Seven actual-time baseline frames remain pixel exact after default hook extraction. Across 135 sampled surfaces, invalid pixel samples fall 50,668→0 and alpha extrema -41.2608…301.9288→0…255. These count repeated surface samples, not artistic quality. Visible head differences are small; raw hidden-RGB changes must not be presented as visible improvement.

Review outputs ../../outputs/evan-cartoon-bounded-surfaces: native-head before/after and branded “missing a favicon”/pause shot, source 8.1875–10.1875 s, normal/quarter 96/384 frames each at 48 fps, all four decode cleanly; sample audit and visible-difference evidence. Selected full-resolution rounded/contact/release/rest frames inspected. No continuous playback/listening acceptance. This is renderer maintenance, NOT a new animation-quality milestone; pinched/gray contacts and mechanical rounded lips remain. Use this valid-sample head as the next artwork-study base, while preserving older comparison modes.

## Latest: anchored face skin

Read CARTOON-EVAN-ANCHORED-SKIN.md. AnchoredCartoonHead extends SeparatedCartoonHead and holds the first 32 skin-ring anchors at original X coordinates; all external anchors retain the articulated jaw/chin target. Oral layers keep their own unchanged targets. This removes the inspected sideburn/ear-ink triangle dragged onto the cheek by rounded vowels. No generated art, bitmap patch, timing or planner change.

AnchoredCartoonSceneBody / render_cartoon_scene.py --anchored-skin integrates the current continuous-wrist/independent-index body and official branding. Old modes/defaults remain baselines. Skin paint is stable under visemes; separately authored cheek acting can be designed later. The lower jaw is not frozen.

29 affected checks pass: anchored skin (5) plus separated jaw/tongue/material/rounding (24). All 489 existing scene-clock samples retain positive skin-mesh orientation (min signed doubled triangle area .9903469), exact oral targets and external jaw anchors. Native cheek-region mean RGB drift at 3.125/4.6667 s falls 9.1234/10.6951→0. Opaque oral cores remain exact. Legacy Anchored-only mode retains cubic overshoot; its tested C/E/F/H fringe changes are bounded to one 8-bit level. The newer Bounded head above corrects sampled head surfaces; other pixel pipelines are unchanged.

Review outputs ../../outputs/evan-cartoon-anchored-skin: same-audio native-head before/after, full branded integration and muted quarter-speed versions; source 2.5–5.0 s, 120/480 frames each at 48 fps; all four decode cleanly. Quarter speed repeats source frames. Selected full-resolution rounded/contact/FV/open-jaw views show clean cheek paint and retained jaw motion. No continuous playback/listening acceptance or studio-quality claim. Pinched lips, mechanical rounded silhouettes and shared tongue targets remain.

## Current construction / prior evidence

Head: separate skin, cavity, teeth, tongue floor/blade, closed lips and FV surfaces; original independent brows. Solid cavity/tilted closure; material-group interpolation avoids skin exposure on FV release. Phone-driven rounding width has authored ±62.5 ms lead/release. SeparatedCartoonHead uses a five-binomial-sample geometry window spanning 83.3 ms (±41.7 ms), transfers 75% H geometry to modest B aperture, retains original H tongue lift and exact current A/G contacts/settled rest. Mouth aperture and chin still share one geometry vector. Prior 40 head checks pass; default hook extraction was pixel exact at seven actual times. Details CARTOON-EVAN-SEPARATED-JAW.md.

Important correction: existing acoustic H already survives energy attenuation; only C/D/E/F are reduced by energy. H is shared by L/TH/DH. Rooted blade uses existing H, not a new predictor or energy fix. One stylized clear-L blade does not resolve dark/coda L or dental contact. Raw generated art/exact prompt/reference in tongue-source; registered blade/original floor/hash manifest in tongue-rig, animationReady=false. Blade-only prototype looked like a hanging uvula and was rejected. Four-layer oral construction PSD reopens at mean premultiplied error .002736/255; not a native Moho rig. CARTOON-EVAN-LINGUAL-STUDY.md.

Body: original layered neck under collar, arm/wrist chains, one independently controlled three-phalange index. JoinedWristArm keeps original forearm grid and extends one continuous skin across fitted wrist/palm; independent index shares the exact distal hand parent. Seven runtime/body PSD layers (right palm part of arm skin). Compact rest uses 70% authored bends/projected lengths, full point preserved; remaining thumb/three neighbors share one drawing and rest is clenched. Prior 23 wrist/hand/scene checks pass across 489 poses; seven-layer PSD error .007254/255 before body roll. CARTOON-EVAN-JOINED-WRIST.md / CARTOON-EVAN-COMPACT-INDEX.md.

Scene: 0–10.1875 s through favicon/pause, two word-anchored gestures with anticipation, holds, follow-through and settle. Browser globe is a missing-favicon example; official mark retained. No actual website update demonstrated. Older complete review films in evan-cartoon-joined-wrist; jaw/tongue studies in evan-cartoon-separated-jaw and evan-cartoon-lingual.

SculptedContactHead / fv-source-v2 / fv-rig-v2 has no convincing release improvement; NOT promoted. Deep index shortening folded the mesh, inward root rotation exposed a cut edge; rejected. Do not force warps to supply missing anatomical drawings. Older checkpoints preserved verbatim in PAINTED-EVAN-HISTORY-2026-10-18.md, -B.md and -C.md.

## Speech evidence

Two-pass PocketSphinx alignment: 66 words/248 phones, 39-phone catalog, diphthong glides, contacts, silence gating. Reference ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All 18 word-anchor flags have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json; retain acoustic timing. Exact boundaries remain UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. This skin pass leaves recording, weights and annotations unchanged.

## Next concrete work / limits

1. PRIORITY: artist-designed clean shallow-contact and rounded-vowel contours, registered as genuine separate components with shared anatomical correspondence. Inspect against selected cartoon source; do not promote a generated concept plate or flatter sprite as a working rig.
2. Separate L/dental tongue controls and consider independent jaw/chin movement under lip seals without delaying contact. Preserve source proportions and audio evidence.
3. Design softer palm/neighbor-finger poses, clean wrist/shoulder linework and critically review acting rhythm. Static legs and missing eye/blink rig remain. A human character artist/animator is needed for final anatomy/performance approval. Native raster detail and CPU rendering constrain iteration; hardware cannot supply missing drawings.

## Runtime

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for test/render batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, user deliverables in outputs/. Inspect alpha art over a solid backdrop; hidden RGB misleads. No unattended Moho actions.
