# Evan animation checkpoint

## Latest direction

The user explicitly replaced the realistic painted look with an entertaining expressive 2D CARTOON. The photograph is a loose identity reference only. Use clean outlines, simple cel colors, readable mouths, flexible poses and playful acting. Preserve dark tousled hair, black sunglasses, navy shirt and black tie. The heartbeat prompt was corrected on this run to match that direction. Its id remains develop-evan-painted-animation, with an hourly schedule and meaningful-milestone notifications only.

## Branch and safeguards

Checkout: work/engine, branch development/evan-painted-rig. Draft PR #4: https://github.com/TeamRovor/rovor-video-engine/pull/4. Commit bounded development changes; never merge/deploy without explicit approval. Preserve main, V3/V4, approved symlinks/updater and original artwork. Do not launch, restart or probe Moho unattended: an earlier native render probe crashed it. Continue the independent local renderer.

## Current sources

Read CARTOON-EVAN-DIRECTION.md and CARTOON-EVAN-SOURCE-REVIEW.md. Concept: evan-character/cartoon-v1/source/design-sheet-v1.png. New setup-v1.png and speech-poses-v2.png establish the cartoon setup and nine speech targets. speech-poses-v1.png failed F/V and L review and is retained for comparison. Prompts are recorded beside the PNGs. The v2 contact poses are improved candidates, not approved animation.

Audit tool: evan-engine/audit_cartoon_sources.py records source geometry, alpha/frame margins and nine actual head component boxes. Do not slice by equal thirds: some hair crosses those lines. The source stage is explicitly unregistered and animationReady=false. New source review deliverables: ../../outputs/evan-cartoon-rig-study. A first experimental registered cartoon head component and 4.8125-second diagnostic film now exist; full-character layered rig is still incomplete. Read CARTOON-EVAN-HEAD-MOTION.md. Registered plates live in cartoon-v1/head-rig; builder and renderer are build_cartoon_heads.py, cartoon_head.py and render_cartoon_head_study.py. Review outputs are ../../outputs/evan-cartoon-head-motion. Narrow mouth/teeth blends remain doubled or soft, and FV still reads as grimace. Do not call the head accepted or the animation finished. The previous head-component suite had 62 passing tests, which do not establish visual quality.


## Latest oral-layer milestone

Read CARTOON-EVAN-ORAL-LAYERS.md. A new optional LayeredCartoonHead separates skin, cavity/outline, teeth, floor/raised tongue, closed lips and FV contact. Built-in imagegen hidden skin/cavity sources and prompts live in oral-source; derived components and hashes in oral-rig; tighter matte registration in head-rig-v2. The original head-rig and default mesh diagnostic remain unchanged. Use render_cartoon_head_study.py --mouth-method layers. 69 tests pass. Review outputs ../../outputs/evan-cartoon-mouth-layers include normal and quarter-speed diagnostic films, native before/after comparison and a reopened seven-layer PSD. Teeth duplication is reduced; the old smile ink is removed from hidden skin. FV still looks like a grimace; tongue gestures remain simplified, and some lip/edge pixels remain rough. No production/studio claim.

Next priority: stop static-head micro-polishing and build hidden-surface torso/arm/hand plates and the body rig, with meaningful cartoon acting. Refine FV/L anatomy with redrawn art/animator help where needed. Preserve old/new films for comparison. All 18 timing flags now have visual evidence review; exact boundaries remain unverified (see latest speech evidence review).

## Latest body-rig milestone

Read CARTOON-EVAN-BODY-RIG.md. Opt-in cartoon_body.py connects LayeredCartoonHead to separate original torso and arm surfaces, with independent shoulder/elbow/wrist FK per side, continuous skinning, delayed follow-through and modest head/body acting. body-rig/manifest.json is explicitly animationReady=false. The generated armless torso changed proportions and failed registration; body-source preserves that rejected candidate and prompt, while runtime uses original source overlap. No hidden-surface success is claimed.

Review outputs ../../outputs/evan-cartoon-body-rig include 4.8125-second normal/quarter-speed narration study, native pose comparison and reopened four-layer PSD. 72 checks pass. Native visual inspection caught/fixed clipped shoulder mattes and an old chin fragment; extra armpit folds, neck transition and edge roughness remain. Hands use one open drawing per side, fingers unrigged, legs static, upper-face expressions absent. More artist-authored/redrawn components and animator acting review are needed. No Moho probe or approved release changes.

## Speech system

Read ACOUSTIC-SPEECH-ALIGNMENT.md. b585490 implements two-pass PocketSphinx acoustic word/phone alignment, a 39-phone General American English catalog, diphthong glides, held vowels, lip contacts and six continuous controls at scene fps. Reference recording: 66 words, 248 phones, 1059 control samples, 18 word-anchor disagreements with visual evidence review and exact boundaries still unverified. Coverage does not establish timing accuracy. Waveform/spectrogram exports show a useful pause/breath suppression after favicon. The earlier speech-system suite had 59 tests. Pipeline fingerprint is 4. Actual planner source is authoritative over historical painted docs.

## Latest speech evidence review

Read SPEECH-TIMING-REVIEW.md and evan-engine/reviews/evan-reference-timing-v1.json. All 18 flags now have waveform/spectrogram visual review in six regions, retaining current acoustic timing; exact phone boundaries remain UNVERIFIED and no listening verification is claimed. Clear Whisper pause/tail errors are documented, including digital ending beyond recording. Do not call these flags unreviewed, resolved or ground truth. Review is tied to exact audio/plan hashes. No timing/gesture weights changed.

New speech_alignment_audit.py exports both hypotheses, sample-clock spectra and context clips; speech_review.py --audit-dir integrates it into new experimental planning runs. Existing cached scenes are unchanged. Spectrogram endpoint stretching is fixed. 75 checks pass; actual narration CLI integration verified. Outputs ../../outputs/evan-speech-timing-audit hold the review page, six graphs/audio clips and pause/onset films using existing cartoon artwork. Body/hand/face defects remain as before.

## Latest separate-hand milestone

Read CARTOON-EVAN-POINTING.md. CartoonGestureBody is a new opt-in study; original CartoonBody remains unchanged. Separate wrist-local open hand drawings and a generated/registered right pointing hand now attach to hierarchical hand transforms. New pivots are wrist [214,762]/[810,762], not old palm-centered positions. Source/prompt and registration matrix/hash live in hand-source and hand-rig. An oversized wrist-stub flap was shortened after assembled review. Thinner hand linework and a visible wrist contour remain; animationReady=false.

The new 4.8125-second normal/quarter-speed narration shot points toward the browser card around globe/up here. It uses a pointing drawing throughout and does NOT demonstrate an open-to-point transition or independently moving fingers. Six actual body/hand pixel layers reopen in PSD and match assembly. Native open/point comparison and stage frames are in ../../outputs/evan-cartoon-pointing. 79 checks pass; no quality inference. Shoulder/armpit, neck, matte, FV and facial-expression limitations remain, and no new hidden shoulder/neck source was accepted. No Moho activity or approved release change.

## Latest local-underarm milestone

Read CARTOON-EVAN-UNDERARM.md. New CartoonSocketBody is opt-in via render_cartoon_gesture_study.py --sockets; earlier body/gesture classes remain baselines. Generated v2 torso source still shifted proportions, so only locally registered underarm bands are used. Center-shirt ECC 0.97885 is a registration diagnostic, not quality confidence. socket-source/socket-rig hold visible input, prompt, source/hash, matrix and patch mask. All pixels outside the masks, including neck/center/tie/legs, remain exact originals. animationReady=false.

Native white/gray comparisons reduce dangling black armpit tabs. Remaining sleeve/torso creases, shading transition and neck/collar join still need cleanup; neck was not repaired. Raw transparent previews can show hidden RGB and exaggerate edge speckles: use actual solid-background composites. Exporter now also writes a gray JPEG preview. 81 checks pass; six-layer PSD reopens and matches assembly. Normal/quarter-speed same-motion films and native before/after are in ../../outputs/evan-cartoon-joins. No Moho activity or approved release changes.

## Latest independent-brow milestone

Read CARTOON-EVAN-EXPRESSIONS.md. ExpressiveCartoonHead uses separately extracted original brows with generated hidden skin only under their footprints. Source/input/prompt, registered skin/ink layers, masks, pivots and hash live in expression-source/expression-rig. Stable-feature ECC 0.99950 is not a quality/confidence score. A regression caught outside-forehead rounding; final code preserves every original pixel outside the edit region. LayeredCartoonHead/default routes remain unchanged. animationReady=false.

Authored ever/tiny/here accents follow aligned word times with holds and continuous independent raise/tilt controls. This is not automatic emotion inference. CartoonExpressionBody and render_cartoon_gesture_study.py --expressions integrate it with the body. New normal/quarter-speed native-head diagnostic, body still, neutral/acting comparison, cue record and reopened three-layer PSD are in ../../outputs/evan-cartoon-expressions. 85 checks pass, not visual acceptance. Hair/glasses restrict range; wide-shot effect is subtle; no eye/blink rig. The native comparison still shows the unacceptable F/V grimace at 0.35 s. Neck/wrist/shoulder and hand linework remain unfinished. No Moho activity or approved release changes.

## Latest F/V contact milestone

Read CARTOON-EVAN-FV-CONTACT.md. FVContactHead is opt-in: generated/registered relaxed contact art is split into local lip/outline and upper-teeth surfaces with new per-instance G geometry. Lip/teeth remain separate pixel layers; contact height is constrained during fading toward vowels. Source/prompt, masks, geometry/hash and limitations live in fv-source/fv-rig. animationReady=false. Old LayeredCartoonHead/expressive/body defaults keep old G and remain baselines. CartoonFVBody and --fv-contact integrate the candidate.

Normal/quarter-speed same-audio old/new diagnostics use V in ever and F/V in favicon, with a labeled review cut (92 frames/48fps). Native peaks and transition frames, reopened three-layer source PSD and body integration are in ../../outputs/evan-cartoon-fv. 89 checks pass; constrained-contact geometry sweep also passes. Grimace is reduced, but the rolled lower lip remains simplified and can read as a narrow tooth hint. No anatomical/studio acceptance or timing correction is claimed. A character artist/animator is still needed for contact and performance review. All other documented join/hand/face limitations remain. No Moho activity or approved release changes.

## Next concrete work

1. Build a clean neck/collar attachment and finish remaining shoulder crease/skinning defects. Local underarm tab cleanup now exists, but is not complete shoulder construction. Preserve original visible art and reject whole-body proportion changes.
2. Clean the new pointing hand linework/wrist contour and add a relaxed hand plus a designed pose transition. Pointing exists as a separate drawing, not individual fingers. Build expression/brow acting; current study is not polished.
3. The 18 timing disagreements have visual evidence review; exact phones still require listening/phonetic annotation. Preserve the review record and uncertainty. Speech-phone coverage and geometric tests do not prove lip-sync accuracy.
4. Refine the new F/V rolled-lip candidate with artist/animator anatomy review, then improve L/tongue articulation and a longer narration scene with a real pause. The old grimace remains the baseline; the new candidate reduces it but is not production-approved. Preserve both.

## Environment

Bundled Python: /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3. Optional packages in ../painted/deps, config ../painted/tools.json. Use absolute PYTHONPATH from this checkout. Original audio is in sibling previous chat's work directory; see speech documentation/earlier outputs for exact paths. Existing local work: ../speech-alignment-v4 and ../painted-life. Previous painted films are archived references only, superseded visually by the cartoon direction.

Continue authorized work autonomously; ask no routine questions. Notify only on meaningful milestones, failures, completion or required user action. Do not stop merely because source art exists. Once a polished cartoon animation with convincing facial acting, useful hand poses and timing is actually ready for review, disable the automation and report that milestone.

## Latest neck attachment experiment

Read CARTOON-EVAN-NECK-EXPERIMENT.md. CartoonNeckBody / --neck is an opt-in diagnostic: separate jaw/head-following neck mesh with a collar-fixed base, corrected head translate [285,-24], seven-layer PSD. Baseline routes preserve original placement/pixels. No generated artwork or Moho action. Neck-rig manifest explicitly animationReady=false.

Native review FAILED larger-tilt acceptance: collar rim remains rough and a gap opens at -8 degrees. Retaining a two-pixel original collar skin rim reduces pinholes but is not new hidden anatomy. Do not call this a completed repair. Normal/quarter-speed authored-range shot and native 0/+8/-8 comparison are in ../../outputs/evan-cartoon-neck. Reopened PSD matches assembly; 92 checks pass, but geometry passing does not fix the visible defect.

Next concrete work: redraw a registered continuous cartoon neck plus clean collar opening/overlap, preserving selected head/body proportions, and rerun this exact stress/word study. Do not keep expanding color-key/dilation workarounds; dilation candidates grew outline/hair colors and were rejected. Other hand/shoulder/FV/performance limitations remain. Full polished milestone remains incomplete; automation stays active.

## Latest registered neck/collar art milestone

Read CARTOON-EVAN-NECK-ART.md. Built-in imagegen produced extended-neck and empty-collar source plates with exact prompts under neck-source. New builder registers only hidden neck plus a local collar patch into neck-art-rig. CartoonNeckArtBody / --neck-art is opt-in; older routes remain baselines. Generated face is discarded; original facial layer matches prior neck study at narration jaw extremes. Working neck and torso are independent, with a fixed collar base and 25% progressive lower-neck width registration.

Native identical-control 0/+8/-8, actual narration jaw extremes and synthetic full-D jaw views show the pale gaps closed and speckled rim removed. A small angular shadow/fold remains below the left jaw; in-plane tilt only, not production anatomy. 95 checks pass, not a perceptual quality rating. Normal/quarter-speed 4.8125/19.25-second films, reopened seven-layer PSD (mean difference .0074/255), native comparisons, source plates/prompts and notes are in ../../outputs/evan-cartoon-neck-art. No continuous film playback or listening verification claimed.

Next concrete work supersedes the prior redraw-neck task: first isolate/fix the muddy brown neutral-to-UW oral blend visible at 4.7917 s in logo (X=.5405/F=.4595, no F/V; unchanged timing), then extend a narration shot through favicon and its pause, design a relaxed-to-point hand transition with anticipation and held word accents, then judge normal-speed motion. Keep the cleaner neck assembly but do not expand in-plane tilt beyond inspected +/-8 degrees. Refine the remaining left-jaw fold during artist cleanup. F/V, tongue, wrist/hand linework, shoulder creases, static legs and limited facial acting remain. All 18 timing flags have visual evidence review; exact phones remain unverified. Preserve main/V3/V4/updater/native Moho; no merge/deploy. Full polished milestone remains incomplete and automation stays active.

## Latest solid oral cavity milestone

Read CARTOON-EVAN-SOLID-CAVITY.md. SolidCavityHead / CartoonSolidMouthBody / --solid-mouth is opt-in. It fixes the muddy neutral-to-rounding intermediate in logo by keeping cavity material opaque through opening, preserving the tilted corner chord while closing, and retaining solid closed ink until the inner opening replaces it. The initial opacity-only attempt revealed a detached line and sparse closure ink; final code addresses those defects. Original source art, word/phone timing and weights are unchanged. All pure poses are exact; older/default routes remain baselines. 100 checks pass, including oral-target orientation and actual rendered pigment/ink regressions; this is not perceptual approval.

New 1.5-second original-audio native-head before/after and six-second muted quarter-speed diagnostic use source 3.75–5.25 s, with actual PCM waveform and existing word labels. Native crop sweep, problem frame, final branded body still and source hashes are in ../../outputs/evan-cartoon-solid-mouth. Problem pixel changes from brown [162,90,59] to dark cavity [79,15,14]; this is one regression, not perceptual acceptance. Inspect full-resolution outputs; no continuous playback/listening verification claimed. Only scratch ../cartoon-oral-transition/compare-final matches the final code; older compare/body batches are superseded.

Next concrete work: improve the narrow rounded contour and assess lip-rounding versus rest/energy weighting through OW transitions; current wedge-like early opening and jagged lips remain obvious. Then extend through favicon/pause and design a relaxed-to-point hand transition with deliberate word accents. F/V/L anatomy, wrist/hand linework, shoulder creases, static legs and missing eye acting remain. All 18 timing flags retain visual evidence review and exact-boundary uncertainty. Preserve main/V3/V4/updater/Moho. Full polished milestone remains incomplete; automation stays active.
