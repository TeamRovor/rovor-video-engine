# Rovor — professional-method animation / voice QA checkpoint

## Branch / safeguards

- Repo: `TeamRovor/rovor-video-engine`.
- Development branch `development/studio-performance-gates`, forked from `development/cartoon-rig-blockout` (which descends from `development/cartoon-acoustic-audit`). **Do not merge or deploy** without explicit authorization.
- Do not modify main, V3/V4, approved updater and symlinks, or native Moho projects. **Do not launch/probe Moho unattended** after the crash.
- Latest direction is **expressive 2D cartoon Evan**; photographs for loose identity reference only. Painted/photorealistic style is superseded.

## Verified research and implemented pieces

- `STUDIO-ANIMATION-AND-ALIGNMENT-PLAYBOOK.md` maps Disney Animation, Pixar, Montreal Forced Aligner, and WhisperX material to shot production and acoustic accuracy gates; the repository includes source URLs.
- `evan-engine/studio_performance.py` implements *editorial-authored* acting beats with named intent, anticipated pose arrivals, holds, independently held arms/head/brows and registered wrist-space hand transitions. It does not infer an emotion from RMS amplitude. Hard fails on overlapping cues, missing intent, out-of-range joints or unsupported pose labels.
- The existing `evan-engine/cartoon_rig_blockout.py` accepts optional `direction=` / `--direction` while keeping the original no-direction API. Mouth audio controls remain independent of acting direction. New illustrative cues are `evan-engine/studio-direction-example.json` and are **not** real-audio acting decisions.
- `evan-engine/studio_alignment_qa.py` verifies acoustic word and phone topology, compares independent estimated word anchors, flags runs of very short phones and low-energy words, reads the original PCM16 audio for measured RMS and a sample-byte checksum when supplied, and optionally measures boundary error against *human-annotated* reference words. A reviewed `revise` without a new corrected plan remains unresolved. The tool never claims model score = confidence, and never auto-adjusts a boundary.
- New tests `test_studio_performance.py` and `test_studio_alignment_qa.py` plus six existing rig tests: **15 focused tests passed locally**. This is not a full repo or real-audio regression.

## Visual diagnostics and limitations

- Locally rendered SVG frames and 1280x720, 24fps films, 96 frames: normal ~3.96s and half-speed ~7.92s. Inspected full-resolution frames at 0.30, 0.55, 0.90, 1.45, 2.48 and 3.55 seconds. Renders rely on **synthetic mouth controls** (not actual Evan audio). In this environment, the official Rovor logo binary wasn't present so a labeled placeholder appears.
- Remaining clearly visible: stiff elbow geometry, spoke-like hands/fingers, rough shoulder connections and lower-face anatomy, overly uniform outlines, no convincing true 2D deform of tongue/lips, no hair/tie offset/follow-through, no fully authored shot staging. These renders are engineering blockouts, **not finished films**.
- The original 22.05s WAV and complete speech plan were not accessible here. Prior **18 suspicious word regions remain pending**; no measurable truth about their real timing has been established.

## Next concrete tasks

1. Retrieve the exact WAV/plan on the authorized Mac checkout. Use `review_acoustic_flags.py` with `--expected 18` and `studio_alignment_qa.py --wav` to inspect each word; retain uncertainty, manually annotate representative word/phone bounds and add optional MFA comparisons. Never silently override the current PocketSphinx timings.
2. Inspect full-resolution `evan-character/cartoon-v1/source/design-sheet-v1.png`, `setup-v1.png` and `speech-poses-v2.png` and redraw/re-register actual layer plates. Do not treat concept sheets, flat sprites, or the current SVG geometry as finished rig art.
3. Resolve F/V lower-lip contact, L tongue, P seal and doubled teeth/line art at previously documented 0.3125 / 0.583 / 0.708-second head frames, plus currently stiff fingers, arm hidden overlaps and elbow contours.
4. Use real narration to editorially time a 4–8-second speaking shot and proper official brand. Review muted acting, then normal-speed with sound, slow speed and 100% PNG frames. Add hair/tie follow-through only after primary posing is convincing.
5. Keep commits bounded on development branches. Preserve branch lineage and checkpoints; leave the agreed polished cartoon review milestone open and the current automation enabled until real criteria pass.

Status: **Engineering and review workflow improved; polished cartoon animation not ready for review.**