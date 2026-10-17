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

Next priority: stop static-head micro-polishing and build hidden-surface torso/arm/hand plates and the body rig, with meaningful cartoon acting. Refine FV/L anatomy with redrawn art/animator help where needed. Preserve old/new films for comparison. All 18 audio timing flags still require review.

## Speech system

Read ACOUSTIC-SPEECH-ALIGNMENT.md. b585490 implements two-pass PocketSphinx acoustic word/phone alignment, a 39-phone General American English catalog, diphthong glides, held vowels, lip contacts and six continuous controls at scene fps. Reference recording: 66 words, 248 phones, 1059 control samples, 18 word-anchor disagreements needing review. Coverage does not establish timing accuracy. Waveform/spectrogram exports show a useful pause/breath suppression after favicon. The earlier speech-system suite had 59 tests. Pipeline fingerprint is 4. Actual planner source is authoritative over historical painted docs.

## Next concrete work

1. Improve the experimental registered cartoon head: separate oral interior/teeth/tongue surfaces and match mouth contours. Inspect documented defects at 0.583, 0.708 and 0.3125 seconds. Upper-face invariance and non-inverting interpolation now work, but source anatomy and line blends are not yet accepted. Seek redrawn/animator cleanup if FV/L remains unclear. Keep existing normal/slow diagnostic films for comparison.
2. Build genuinely separate head, neck, torso, arms and useful hands with hidden overlap surfaces. The setup PNG is flattened source, not an articulated rig. Export real editable layers and verify reassembly.
3. Extend the acoustic-driven head component into a genuine cartoon body rig, then render a short narration acting shot, especially P in open at 0.60–0.65 s, F/V/L and a pause. Review normal speed, slow speed and full-resolution sequences against the concept. No studio claim from tests or sprite swaps.
4. Review the 18 timing disagreements against audio/spectrogram evidence. Keep uncertainty and estimated fallbacks visible.

## Environment

Bundled Python: /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3. Optional packages in ../painted/deps, config ../painted/tools.json. Use absolute PYTHONPATH from this checkout. Original audio is in sibling previous chat's work directory; see speech documentation/earlier outputs for exact paths. Existing local work: ../speech-alignment-v4 and ../painted-life. Previous painted films are archived references only, superseded visually by the cartoon direction.

Continue authorized work autonomously; ask no routine questions. Notify only on meaningful milestones, failures, completion or required user action. Do not stop merely because source art exists. Once a polished cartoon animation with convincing facial acting, useful hand poses and timing is actually ready for review, disable the automation and report that milestone.
