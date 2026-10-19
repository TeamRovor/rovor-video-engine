# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON, not the superseded realistic painted direction. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photograph supplies loose identity cues only. Preserve hair/glasses/navy shirt/black tie and official Rovor branding. No rejected geometric mouth patches, skin stickers or flattened head/body replacements.

Repo work/engine; branch development/evan-painted-rig (legacy name). Draft PR #4 https://github.com/TeamRovor/rovor-video-engine/pull/4 based on experiment/moho-native-rig. Commit/push bounded development work only; never merge/deploy without explicit approval. Main stays 4e099b5f1a30661c952358f49e1e2d70a5fe2a62; origin/feature/evan-v4 stays 27b664b9daa924ff17d3b874264bc4cef7131196. Preserve V3/V4, approved releases/symlinks/updater and native Moho projects. Do not launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation remains ACTIVE. Notify only meaningful review milestones/failure/completion/required action; routine decisions are authorized. Full polished cartoon animation milestone is NOT complete. Disable automation only once it actually is ready for review.

## Latest: broad cavity/rim artwork candidate

Read CARTOON-EVAN-BROAD-CAVITY-ART.md. Built-in imagegen edits the original isolated broad cavity to remove the painted red floor; retained cavity gradient is acknowledged despite flat-fill prompt. Source/reference/exact prompt in broad-source-v1, chosen broad-mouth-v1.png SHA 85e71f85065c5e86b3f41a2b667732851d348c33111c41a6b5ee61df073b5da9. Reference hidden RGB was zeroed only where alpha=0; visible source unchanged. New broad-rig-v1 has separate cavity/rim/matte, canonical affine C fit [195,316,281,361], alpha>=250 normalized, 12-source-pixel underlap and 4x sampling. Manifest animationReady=false with hashes/matrix/generation chain. Source pixels rebuild exactly. Two-layer C-space PSD reopens at mean premultiplied error .0004806/255; not full/native Moho rig.

BroadCavityCartoonHead / --broad-cavity extends the lighter O/contour rig. Cavity/rim warp independently; matte clips separate teeth/tongue. New default-pass-through broad-surface/matte hooks preserve previous modes; LightLip actual frames at 2.69/3.125/4.6666667 s remain pixel exact. Old artwork modes/defaults, phone identity/timing, geometry, brows and body are unchanged. 22 targeted checks pass (5 new +17 prior); closure/FV/full-rounded X/A/G/E/F stay exact, broad changes local and tongue clipped. All 489 geometry targets remain exact; 67 partial rounded states have zero fallback. All four final films decode cleanly: normal/quarter 120/480 frames at 48 fps (2.5/10 s), source 2.5–5.0 s.

Review ../../outputs/evan-cartoon-broad-cavity: normal/quarter native-head comparison and branded integration, source 2.5–5.0 s. Initial native broad contour is cleaner and baked red floor gone, but grey upper strip persists in the old upper-teeth surface; do NOT claim this source fixes all brown/grey shading. Shallow B/FV contact/release still needs new construction. Keep OPTIONAL; no default promotion, polished or studio claim. No continuous playback/listening acceptance. Full milestone incomplete; automation remains ACTIVE.

## Prior: lighter rounded source artwork

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

1. PRIORITY: redesign/register the upper-teeth band and shallow B/FV contact/release. The new broad cavity removes the painted floor and cleans the outline, but remaining grey upper strip implicates the old tooth surface; Ablation at frame 148 removes only the upper-teeth contribution and the grey strip disappears (Upper-Teeth-Diagnostic.jpg; render_broad_teeth_diagnostic.py). Inspect cumulative rounded-phone opacity factors plus tooth placement and lip occlusion before redrawing; At frame 148 the existing two rounded-tooth opacity factors .6820×.7827 leave .53385 before source alpha/matte; control evidence is in Review-Evidence.json. The ablation is not a proposed tooth-free design. Keep broad and lighter-O candidates optional; no more full-head swaps or alpha layers. Use the concept's simple shapes and seek artist approval for final anatomy.
2. Distinct L/dental tongue controls and independent jaw/chin under lip seals, preserving exact current contact timing. No invented measured phonetic precision.
3. Softer palm/neighbor-finger drawings, wrist/shoulder linework and more expressive acting/eyes. Do not expand scope once the agreed polished milestone actually is ready.

## Runtime / history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; PYTHONPATH=../painted/deps:evan-engine from repo. Always cv2.setNumThreads(1) for render/test batches. Recording /Users/amarhavic/Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav (mono PCM16). FFmpeg sibling work/media-tools/ffmpeg. Scratch in work/, user deliverables in outputs/. Inspect alpha art over solid backdrop; hidden RGB misleads.

Previous checkpoint archived verbatim as PAINTED-EVAN-HISTORY-2026-10-19.md; older histories -2026-10-18.md / -B.md / -C.md retained. Read specific design/review docs rather than restoring superseded defaults.
