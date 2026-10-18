# Rovor V11 — physical cloth-protection animation pass (review only)

This does **not** restart the film. It is an editable action-scene replacement for the original Evan Oct 6 narrated painting explainer, source **[108.0,114.0)** seconds, exactly **360 native 60fps frames per orientation**.

## Immutable identity

- Narration SHA256: `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`.
- Original `ElevenLabs_2026-10-06T01_10_34_Big Steppa Evan ...v4.mp3` is private and **not included in this ZIP or GitHub**.
- Evan's original head/body rig, dark tousled hair, sunglasses, navy shirt, black tie remain unchanged. The painter is an educational secondary character; this video does **not** assert actual client outcomes.
- Prior V9B full reviews and editable ZIP are retained unchanged. `main` must not be merged or modified.

## Scene action

1. A deliberate close-up cut reframes the secondary painter and couch (rather than a tiny, static full-body actor).
2. The painter grips a sheet, pulls it across the furniture, forming changing folds and visibly moving the sheet's front hem and backrest covering.
3. The painter tucks and releases the cloth with connected shoulder/elbow/forearm/cuff/hand art, and the cloth settles.
4. Landscape and portrait are authored as different compositions; both have scalable editable SVG vector frames.

## Reusable engine components

- `fabric_protection_v11.py`: deterministic `svg_frame(t, orientation)` and contact coordinates, surface stages, joint/hand geometry. All frame drawing derives from the same mathematical physical actuation state.
- `render_v11.py`: original SHA-locked MP3 cut to [108,114) with native 1080p60 video and one real voice stream. Private MP3 must be staged in the local project folder before running.
- `splice_verified_source.py`: generic 60fps frame-precise video replacement using one continuous unaltered source *recording* re-encoded to AAC, independent from any chosen video topic or speaker; useful for future YouTube productions.
- `verify_v11.py`, `verify_full_v11.py`, `compare_v11.py`: decoded-frame, original-source audio and practical visual delta checks. Motion scores are aids to review, **not a studio quality endorsement**.
- `test_fabric_protection_v11.py`, `test_splice_verified_source.py`: contact-geometry, source integrity, frame bounds and fail-closed future video-splice tests.

## Non-negotiable caveats

- This is still a relatively flat vector cartoon and **NOT Hollywood/studio artistic quality**. The painter's facial performance and hand anatomy need artist-drawn poses. The storyboard timing and full-length phoneme boundaries are not human-certified. Foley, music and advanced garment dynamics are missing.
- Art may only be considered creatively approved after watching normal-speed sound and muted motion, checking hand/cloth contact and visual coherency at every cut. Passing code tests, higher motion scores, or fully decoded frames **do not** approve the movie.
- Older [0,108) and [114,156.2833) review footage is preserved from V9B; full review runtime is still **2:36.283** and remaining coverage to the original 4:22.687 narration is **1:46.404**.
- Do not extrapolate six seconds of stronger animation into a claim that the full film is now polished. Do not alter the final audio brand sign-off without user consent.

## Continuation

Prioritize original hand-drawn painter gestures, realistic fabric weight and stronger acting across all previously flagged slow-motion sections. Build re-usable source art, keep independent portrait and landscape compositions and maintain a non-destructive rendering/QA ledger. After this, develop [156.2833,262.6873) with the original narration and return for a *whole-film* artistic pass. No public deployment or merge.