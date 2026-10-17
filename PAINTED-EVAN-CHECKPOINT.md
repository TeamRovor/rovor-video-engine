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

## Next concrete work

1. Repair visible armpit/neck seams with genuinely registered hidden-surface art. Do not accept generated replacement artwork that changes proportions; preserve original drawing and explicit rejected candidates.
2. Add distinct relaxed/pointing hand drawings and an expression/brow rig; current open-hand FK study is not polished acting. Review full-resolution source and normal/slow film before increasing motion range.
3. The 18 timing disagreements have visual evidence review; exact phones still require listening/phonetic annotation. Preserve the review record and uncertainty. Speech-phone coverage and geometric tests do not prove lip-sync accuracy.
4. Improve F/V and L anatomy with redrawn art/animator review, then render a stronger narration-driven scene with an actual pause and meaningful pointing gesture. Preserve the current baseline films for comparison.

## Environment

Bundled Python: /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3. Optional packages in ../painted/deps, config ../painted/tools.json. Use absolute PYTHONPATH from this checkout. Original audio is in sibling previous chat's work directory; see speech documentation/earlier outputs for exact paths. Existing local work: ../speech-alignment-v4 and ../painted-life. Previous painted films are archived references only, superseded visually by the cartoon direction.

Continue authorized work autonomously; ask no routine questions. Notify only on meaningful milestones, failures, completion or required user action. Do not stop merely because source art exists. Once a polished cartoon animation with convincing facial acting, useful hand poses and timing is actually ready for review, disable the automation and report that milestone.
