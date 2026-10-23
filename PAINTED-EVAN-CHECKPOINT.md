# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photo is loose identity only; realistic painted direction superseded. Dark tousled hair, sunglasses, navy shirt/black tie, official Rovor branding. No facial photo crops, geometric mouth stickers or flattened character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draft PR#4 https://github.com/TeamRovor/rovor-video-engine/pull/4. Development commits/pushes authorized. NEVER merge/deploy without explicit approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4=27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful review milestone/failure/completion/required action only; disable when actually ready. Routine decisions need no question.

## Latest: contact-context candidate rejected after actual comparison

Read CARTOON-EVAN-ROUNDED-CONTACT-STUDY.md. Tested retaining vowel rounding independently of the bilabial contact envelope, preserving actual material/jaw weights and full F/V contact. Candidate passed36 tests and1307 geometry samples, but native render differences were marginal and recording-wide width motion did not improve. All six changed engine/test files restored exactly to55c58b8. Runtime control code is UNCHANGED. Reproducible zero-context diff archived in reviews/rejected-rounded-contact-context-v1.patch; decision in reviews/rounded-contact-study-decision-v1.json. Do not reintroduce that removal of contact suppression/weighting as a presumed fix.

outputs/evan-cartoon-rounded-contact-study: three voiced A/B native-head comparisons plus muted quarter-speed movies. Source696..767,864..935,960..1007; normal72/72/48, slow288/288/192, all six fully decode. Source/AAC decoded samples24000/24000/16000 exactly. All192 native mouth pairs plus full725/887/979/983 visually inspected; prior emulator equals frozen888 pixels exactly; chin/upper identity preserved. No independent listening/continuous-playback acceptance. No new artwork, body rig or Moho bones. No pending jobs.

P width step724→725 improves13.21855→10.18167px; more/AO lower step12.11368→11.56342px. However full-recording maxwidth remains14.60095, p95 grows8.29631→8.35216;18 width steps grow>1px, including977→978 .25833→8.29440 before up/all. These are geometry differences, NOT proof of perceived speed/quality. Full lowerY max14.66776→14.00381; chin exact. Reject adoption because no convincing general animation improvement demonstrated, rather than promote a small local gain from passing tests.

NEXT: test a shared P/B/M approach/seal/release trajectory with authored corner endpoints and a held complete seal, against ALL recording contexts including up/all. Preserve actual phone/sample timing and independent chin. This is a hypothesis, not guaranteed sufficient: thin closed/FV drawings and limited corner/jaw expression still need artist/animator review or matched redraws. Do not use word-specific exceptions, blind global smoothing, retiming or accumulating runtime profiles. Original18+3 acoustic flags remain unverified.

## Working rig retained

55c58b8 matching jaw-skin correction remains active only in opt-in SeparatedOralReview: same registered construction-skin-v1/working-face-skin.png as upper face, authored AA ownership mask/SOURCE UVs/jaw_cut, right329 excludes ear. It is existing registered generated underpainting combined with original skin, NOT recovered artist-original anatomy. Preserves original chin/shadow; rejected generated bright patch/duplicated-ear trial remain archived. No source alpha cleanup.

CARTOON-EVAN-MATCHED-JAW-SKIN.md and outputs/evan-cartoon-matched-jaw retain the complete five-second Rovor body/staging proof:240 voiced/960 muted slow frames,80000 original/decoded samples, two6-plane body/two10-plane native oral PSDs, inspected native240 mouth crops/four stage/six heads.16 focused runtime tests previously passed. Upper288exact240/nose0,minjaw34.1123924,arms494.6158371/135.3514946,fallback0. Body PSD before global roll; native oral planes not body registered/native bones.

Previous checkpoint HISTORY-2026-10-23-I. Earlier histories retain all source/artist studies and18+3 acoustic warnings. Source planSHAaf01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e unchanged. Native512 raster art and restrained face/finger acting remain limits; local8GiB CPU renders proofs but cannot supply missing artwork. No Moho/merge/deploy. Full polished milestone incomplete.
