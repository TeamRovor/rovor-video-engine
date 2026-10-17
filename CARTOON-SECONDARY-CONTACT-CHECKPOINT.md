# Rovor Cartoon Evan — secondary action / F-V oral contact checkpoint

**Status:** 2026-10-17 engineering art refinement. NOT final approved cartoon artwork, NOT a validated real-voice production render. The user's established expressive original 2D cartoon direction overrides generic external workflow suggestions.

## Parent and scoped work

Fork from `development/cartoon-mouth-hands-pass`. The exact built-in six acoustic controls, director-authored independent acting cues, independent wrists/arms/hands, original `main` / V3/V4, updater and Moho preservation stay intact. No Moho launch, merge, or deployment.

- `evan-engine/cartoon_secondary_motion.py`: deliberate secondary action based on the already-authored head and torso pose at three neighboring times. Outputs bounded hair rotation/offset and tie rotation/lift, with lag that settles on a held pose. **No** random movement, amplitude-triggered shaking, or synthetic emotion model.
- `evan-engine/cartoon_rig_blockout.py`: registered front-hair group receives bounded secondary motion; independently layered tie pivots below the knot instead of rigidly following the torso. Existing `frame_svg(t, plan=None, brand=None, direction=None)` and articulation remain compatible.
- `evan-engine/cartoon_mouth_surfaces.py`: revised **F/V** upper-incisor plate and separately clipped rising lower lip/contact band; fades the generic lower-lip outline during strong F/V to avoid cross-strokes. Prior grin-like F/V had incisors floating above a dark slit. Labiodental contact opacity falls to zero under a bilabial seal; tests inspect this.
- Added focused numerical/time-domain and SVG layer validation in `test_cartoon_secondary_motion.py` and amended `test_cartoon_mouth_surfaces.py`.

## What was actually checked

- **23 focused unit tests pass locally:** baseline rig, hand morph, mouth, director-authored performance and new secondary-action tests. These do not prove artistic readiness or spoken-word accuracy.
- Re-rendered **96 full-size 1280×720 frames at 24 fps**, editable source SVG frames and two diagnostic muted films: ~3.96s at normal speed, ~7.92s at half speed. The pose plan is a **synthetic illustrative directing fixture** and the mouth articulation is synthetic (no real Evan audio here). Render manifest explicitly sets `animationReady=false` and `brandAssetVerified=false`.
- Inspected F/V, MBP, open, round, L and grin mouth sheet; six full-frame key poses and the transition sequence. F/V reads more like teeth over a raised lip than the earlier narrow white grin, but still needs artist anatomy refinement. Hair and tie follow-through remain subtle and purposefully settle after movement.

## Unresolved defects and next production actions

1. **Character artwork**: this is a crisp but mechanical blockout. Author/register actual clean hand, arms, hair, face and teeth layers from native-size `evan-character/cartoon-v1/source/design-sheet-v1.png`. Current hand shape and bent elbows are visibly simplistic, and the smile/FV contours still need human artistry.
2. **Real take**: the actual ~22s Evan source WAV/plan is not accessible in this environment. Audit the **18** flagged alignment regions at original sound and native spectrogram. No timing values were claimed fixed; no real audio-driven sync was rendered.
3. **Brand**: the actual verified Rovor logo was not available locally. Rendering uses a clearly labeled placeholder. Do not accept this as a release-quality branded shot.
4. **Acting and clean-up**: build a real narration-aligned 4–8s scene with deliberate gesture choices, pleasing silhouettes, hidden shoulder/elbow overlaps, proper lip landmarks and action beats. Review normal sound speed, slow playback, 100% source frames and muted acting readability.
5. Run full regression on authorized checkout, confirm repo branch state, and only present the actual final polished cartoon for user review when artwork and true audio metrics pass.

**Continue on development branches only. Keep automation enabled; do not infer studio-quality certification from tests or this short diagnostic film.**