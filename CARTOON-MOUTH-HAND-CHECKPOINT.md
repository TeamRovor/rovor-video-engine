# Cartoon Evan: mouth surface and hand deformation checkpoint

**Status: experimental engineering blockout. Not approved production artwork, visual quality, or verified narration lip sync.**

## What changed

- `evan-engine/cartoon_hand_deform.py`: previously experimental hand joint morph now covers finger roots with the palm after rendering articulated fingers, avoiding competing outlines through the palm. All five hand poses share topology; no sprite-opacity dissolve is reintroduced.
- `evan-engine/cartoon_mouth_surfaces.py` (new): constructs one closed cavity path and a registered clip mask around separately identified `oral-interior`, `upper-teeth`, `tongue`, `upper-lip`, `lower-lip`, and `bilabial-closure` surfaces. Adds an explicit sealed-mouth line (no dark gap), round-vowel constriction, distinct F/V narrow upper-tooth contact and L tongue-tip elevation. Face upper region remains in the independent head; jaw offset remains in the jaw transform.
- `evan-engine/cartoon_rig_blockout.py`: uses the new mouth component in the existing editable SVG hierarchy without changing the existing acoustic six-control contract or director-authored acting timeline.
- New focused geometry tests check distinct contact modes, closed-path topology, no duplicate layer IDs, 5 hand types, finite and continuous shared finger landmarks, and full-frame editability.

## Actual validation in local sandbox

- **18 targeted tests passed** (`test_cartoon_rig_blockout`, `test_studio_performance`, `test_cartoon_hand_deform`, `test_cartoon_mouth_surfaces`). Not a complete repository regression.
- 96 rendered full-resolution SVG + PNG frames at 1280x720, 24 fps, with **3.9583 s normal-speed** and **7.9167 s half-speed** muted MP4s. The demo uses **synthetic mouth controls** and illustrative director-authored beats, NOT Evan's real recording. Inspection performed at native-frame and multi-frame contact-sheet size.
- Separate 7-pose mouth sheet visually inspected for rest, M/B/P seal, open vowel, rounded vowel, F/V, L, and grin.

## Critical visual findings

Changes reduce doubled mouth strokes, avoid dark interior on full lip seal, make round-vowel width visibly different, and remove finger roots drawn as overlapping lines on top of the palm. However, the current hand silhouettes still look angular/spoke-like, and F/V looks more like a narrow grin than convincing incisors contacting lower lip. Tongue, teeth and face proportions are still generic procedural artwork, not matched to the approved `cartoon-v1/source/design-sheet-v1.png`. Shoulder/elbow sleeves are stiff, with no convincingly offset hand follow-through. The current 4-second synthetic exercise is not entertaining finished animation. **Do not call this studio-quality.**

## Next high-value tasks

1. Access and inspect the actual concept/setup/speech source PNGs at native size in the authorized Mac worktree. Draw *registered*, topology-consistent mouth, teeth, jaw, tongue, open hand, pointing hand, and curled hand silhouettes against approved cartoon anatomy, not inferred from generic SVG shapes.
2. Fix documented F/V and L ambiguity by drawing true contact shapes and play at size and 24/48 fps, with layers isolated and contour artifacts inspected. Improve hand silhouette and finger articulation, especially wrist angle and elbow overlap.
3. Retrieve actual WAV and acoustic speech plan, inspect all 18 disputed word regions using waveform + spectrogram and normal/slow playback, retain unknown decisions. Include actual official Rovor logo and remove unverified placeholder only when the real asset is present.
4. Build real **narration-driven** acted shot and inspect at normal and slow speeds. Do not substitute synthetic mouth motion, tests, flattened atlases or mute blockout films for voice sync or polished performance.
5. Preserve main, V3/V4, approved updater/symlinks and native Moho; do not launch/probe Moho unattended. Work on development branches, no merges/deploys.

**Milestone still open; automation stays on.**