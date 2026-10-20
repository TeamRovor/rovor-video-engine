# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive2D CARTOON; realistic painted style superseded. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Original photograph supplies loose identity cues. Preserve hair/glasses/navy shirt/black tie and official Rovor mark. No photographic facial crops/geometric mouth stickers/flattened replacement.

Repo work/engine; branch development/evan-painted-rig (legacy name), draft PR#4 https://github.com/TeamRovor/rovor-video-engine/pull/4, base experiment/moho-native-rig. Commit/push bounded development work only. Never merge/deploy without explicit approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4 27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE; complete polished milestone is NOT ready. Routine decisions authorized. Notify meaningful milestones/failure/completion/required action only. Disable only once the agreed polished milestone is actually ready.

## Latest: separate registered dental tip (optional study)

Read CARTOON-EVAN-DRAWN-DENTAL.md. DrawnDentalCartoonHead / render_cartoon_scene.py --drawn-dental uses a NEW broad coral source drawing for TH/DH, retaining original raised L. Built-in imagegen source: dental-tongue-v1/source/dental-tip-v1.png,1254px alpha. Prompt-Set.json and Provenance.json include exact prompt/reference hashes. Separate registered tip.png on512px H canvas, root(237,354),approx36×34px; tip.json records registration. Premultiplied AREA reduction then LINEAR placement preserves alpha. No whole-face patch. Source plate is NOT a registered rig until this separate placement/posing/masking step.

First36×29 placement too low/hidden in inspected native87/258/325 comparisons. Final34px height reaches incisors; TH/DH-only front-tip contact covers lower1.5px of original tooth columns within tooth alpha; upper teeth/lip boundary protected. Floor covers root. L/direct controls exact. Overlapping L/dental supports share an interpolated alpha contour before color blending; no fallback observed. Same acoustic kernels/H energy/jaw/face/brows/body/scene/timing. Previous flattened-L experiment remains rejected/optional; defaults unchanged.

outputs/evan-cartoon-dental-tongue: normal native-head72frames/1.5s three0.5s DH/L/TH excerpts with exact concatenated original audio, quarter-speed288frames/6s muted; branded scene source312–359(6.5–7.5s)48normalframes/1s voice,192slowframes/4s muted. All1280×720/48fps. All4films decode clean; normal audio24000/16000samples16k. All24Lframes exact; dental changes7DH/9THframes,max289/270headpixels. All72captured tongue surfaces bounded/premultiplied; dental morph/FV/dental/rounded fallback0. Seven tests pass(3new+4phone isolation). Test success≠artistic approval.

Full-resolution source/cream composite; native head87/129/258/325; final panel11/29/61; whole scene325 inspected. The tip is broader and reaches teeth, but subtle at scene scale. Four editable actual construction planes in Dental-Construction.psd reopened correctly: back tip,floor,upper incisors,front contact. Before lip masking, NOT full-head/native Moho rig. Global/local premultiplied compositing errors .001021/.133546 per255. Audio-Contact-Review.png waveform/25ms Hann5ms-hop FFT inspected: DH/TH regions weak; labels are existing aligner boundaries, NOT newly verified onset/offsets. No retiming; no independent continuous playback/listening acceptance.

## Retained systems / limitations

RootedFloor / --rooted-floor full0–10.1875s489normal/1956slow reference remains in outputs/evan-cartoon-rooted-floor-full. It uses real tongue blade/floor, continuous H lift/retraction, floor above root; H originally sharedL/TH/DH. Optional duration jaw reduces short-vowel excursion; shared chin not independently animated. Geometry cache max4 inverse fields/dynamic pixels freshly sampled. See ROOTED-FLOOR and DURATION-JAW docs/history for evidence.

Body:7real layers, independent arms/wrists/3-phalange index, joined forearm/palm skin; compact index rest70%curl. Neighbors/thumb still share drawing; legs static. Scene has2word-anchored point accents, anticipation/holds/follow-through/settle and official branding. Eyes/blinks, broader hand acting and shoulder/wrist linework remain unfinished.

Speech:66words/248phones/39ARPABET catalog, two-pass acoustic alignment, diphthong glides/contacts/silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All18flagged anchors have waveform/spectrogram visual review in evan-engine/reviews/evan-reference-timing-v1.json, exact boundaries UNVERIFIED. Preserve acoustic timings until evidence warrants correction. Coverage≠accuracy.

## Next concrete work

1. Review a longer spoken phrase for readable jaw/lip transitions, stressed short-vowel undershoot and heavy lip-corner spurs. Coordinate independent chin/jaw and lower-inner-lip drawings; do not spend further cycles exaggerating this small dental tip or regenerate the whole head.
2. Add a deliberate expression/eye/blink accent and less clenched palm/neighbor-finger poses, keeping the selected cartoon identity. Human character artist/animator still needed for final anatomy, redraw/inbetweens and performance approval. More pixels/faster hardware cannot supply those drawings.
3. Continue real-voice normal/slow full-head/full-scene review; preserve all release safeguards. Full polished milestone still incomplete.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo; cv2.setNumThreads(1). Local8GiB/8logical CPUs, CPU raster sampling; use temporary caffeinate scoped to long renderer/encoder, allow display sleep. Completed this pass; no pending renders. Recording sibling referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav monoPCM16. FFmpeg sibling work/media-tools/ffmpeg. No scipy installed; FFT evidence uses numpy/matplotlib, MPLCONFIGDIR in work/. Scratch work/cartoon-dental-tongue. User deliverables outputs/.

Previous checkpoint archived PAINTED-EVAN-HISTORY-2026-10-20.md; prior -2026-10-19-G/-F/-E/-D/-C/-B retained. Do not restart completed full renders or treat partial old duration frames as a complete baseline.
