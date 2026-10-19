# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON, not the superseded realistic painted direction. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photograph supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No rejected geometric mouth patches, skin stickers or flattened head/body replacements.

Repo work/engine; branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4 based on experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Main stays 4e099b5f1a30661c952358f49e1e2d70a5fe2a62; origin/feature/evan-v4 stays 27b664b9daa924ff17d3b874264bc4cef7131196. Preserve V3/V4, approved releases/symlinks/updater and native Moho projects. Do not launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Notify only meaningful review milestones/failure/completion/required action; routine decisions are authorized. Full polished cartoon animation milestone is NOT complete. Disable automation only once it actually is ready for review.

## Latest: lighter rounded source artwork

Read CARTOON-EVAN-LIGHTER-LIP-ART.md. Built-in imagegen edited the isolated prior rounded mouth with the selected cartoon sheet as style context. New source removes the thick peach lip band and baked red floor. A second flattening edit did NOT remove all gradients; retain this limitation honestly. Both raw outputs/exact prompts in light-lip-source-v1; chosen light-mouth-v2.png SHA d2b759ad9cc454d087a13c289d4bde1fe68753fb0252099fa4bbc4e9c8510e50. It is source art, not a complete rig.

build_light_lip_art.py registers separate cavity/rim and interior matte in light-lip-rig-v1. Canonical affine E fit [211,320,240,366], not anatomical registration; source bounds [491,445,802,845], alpha >=250 normalized, 12-source-pixel underlap, 4x sampling. Manifest records hashes, complete generation chain/matrix/limits; animationReady=false. Registered pixels rebuild exactly. Two editable source-space PSD layers reopen at mean premultiplied difference .0003315/255; not native Moho/full rig.

LightLipCartoonHead / --light-lip inherits the prior contour/tongue rig and current articulated body. Nonrounded controls remain exact; rounded target geometry/audio/planner/contact identity/timing are unchanged. Original modes/defaults remain baselines. 17 targeted checks pass (5 new plus 12 existing contour/rounded-art checks), covering source coverage, exact nonrounded controls, oral locality, transition coverage and separate tongue occlusion. Across all 489 scene-clock targets geometry remains exact; 67 partial rounded states have no fallback. Unequal 50%-alpha silhouette pixels before/after correspondence total 20,296→813 (repeated states; correspondence only, not artistic quality or speech accuracy).

Review ../../outputs/evan-cartoon-light-lip: same-audio native-head comparison and branded shot through “little globe … your logo”/settle, source 2.5–5.0 s, normal/quarter 120/480 frames at 48 fps; all four final films decode without errors. Chosen source/exact prompts/registered components/matte/two-layer PSD/evidence are included. Initial native held-vowel view is cleaner without peach band/duplicated red floor, but tongue/cavity shading are still heavier than the concept's tiny O. Entry still has the older C-mouth brown strip; shallow contacts remain pinched. Keep OPTIONAL; no default promotion or polished/studio claim. Selected native frames inspected; no continuous playback/listening acceptance.

## Existing rig and evidence

Head chain: separate skin/cavity/teeth/tongue floor+blade/closed lips/FV; authored brows; solid cavity; premultiplied oral material interpolation; ±62.5 ms rounded-width lead/release; independent 83.3 ms binomial geometry easing; anchored cheek skin; bounded sampled head surfaces; optional radial outer-contour correspondence before colour mixing. Largest 50%-alpha contours sampled at 4x, 256 outermost rays; interior masks follow the same remaps. This is outer-envelope approximation, not inner-lip/anatomical correspondence. Fully nonrounded/rounded endpoints bypass extra contour resampling. Prior rounded-source and contour modes stay optional. See CARTOON-EVAN-CONTOUR-CORRESPONDENCE.md, -ROUNDED-ART.md, -BOUNDED-SURFACES.md, -ANCHORED-SKIN.md, -SEPARATED-JAW.md and -LINGUAL-STUDY.md.

Jaw aperture/chin still share a geometry vector. Existing H already survives acoustic energy attenuation; only C/D/E/F are attenuated. H is shared by L/TH/DH; rooted blade does not establish distinct dental contact or dark/coda L. Prior 63 head checks passed at 9520001; this pass does not re-label old coverage as new validation. Earlier sculpted FV/contact candidate was rejected for poor release and remains excluded.

Body: continuous forearm/wrist/palm skin plus independent 3-phalange right index on shared distal hand parent; original forearm grid retained/extended. Seven runtime/PSD layers include neck under collar and independently articulated arms. Compact index rest uses 70% authored curl while full-point pixels remain exact. Thumb/three neighbors share a drawing; rest remains clenched. Wrist/shoulder linework, static legs and missing eye/blink rig need work. See CARTOON-EVAN-JOINED-WRIST.md / -COMPACT-INDEX.md.

Scene: 0–10.1875 s through favicon/pause; two word-anchored gestures with anticipation/holds/follow-through/settle. Official mark and missing-favicon browser-globe example retained; no actual website update demonstrated. Earlier full films in evan-cartoon-joined-wrist; recent focused movies in evan-cartoon-contour and evan-cartoon-light-lip outputs. Source pixels/CPU raster warping constrain detail and iteration; greater output resolution cannot supply missing drawings. Human character artist/animator needed for final anatomy/performance approval.

## Speech evidence

Two-pass PocketSphinx alignment: 66 words/248 phones, 39-phone catalog, diphthong glides, contacts and silence gating. Plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json. All 18 word-anchor flags have waveform/spectrogram VISUAL review in evan-engine/reviews/evan-reference-timing-v1.json. Exact boundaries remain UNVERIFIED; no listening/ground-truth acceptance. Coverage is not accuracy. Preserve acoustic timings until evidence warrants a correction. This art pass leaves recording, weights and annotations unchanged.

## Next concrete work

1. Design clean broad/shallow mouth construction, beginning with B/FV contact and release: remove the older C-mouth brown strip through better source drawings/registration, not more full-head swaps or alpha layers. Keep the lighter O optional until performance review. The chosen concept's simple inked shapes are the design reference; an artist should approve anatomy.
2. Distinct L/dental tongue controls and independent jaw/chin under lip seals, preserving exact current contact timing. No invented measured phonetic precision.
3. Softer palm/neighbor-finger drawings, wrist/shoulder linework and more expressive acting/eyes. Do not expand scope once the agreed polished milestone actually is ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for render/test batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, user deliverables in outputs/. Inspect alpha art over solid backdrop; hidden RGB misleads.

Previous checkpoint archived verbatim as PAINTED-EVAN-HISTORY-2026-10-19.md; older histories -2026-10-18.md / -B.md / -C.md retained. Read specific design/review docs rather than restoring superseded defaults.
