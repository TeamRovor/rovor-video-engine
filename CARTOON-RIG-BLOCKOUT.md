# Cartoon Evan — independent SVG rig blockout checkpoint

**Status: engineering blockout; NOT an approved character or polished animation.** The most recent user direction remains an entertaining, expressive 2D cartoon. A photograph is useful for loose identity cues only. Never resume the earlier realistic painted presentation.

## Bounded deliverable

`evan-engine/cartoon_rig_blockout.py` renders independent SVG paths and hierarchies for head, upper face, moving jaw, oral cavity, teeth, tongue, lips, separate brows, neck, torso, upper arms, elbow hinges, forearms, wrists and five useful hand poses. The arms have separately keyed shoulder/elbow/wrist curves. Synthetic short acting cues give held expressions, anticipation and settle. Hand-pose changes cross-dissolve briefly in a common registered wrist space rather than jumping between full-body sprites. The source SVG layers remain editable and independently articulated.

The mouth consumes the **existing** `finalize_plan` six-control contract (`jawOpen`, `lipSeal`, `lipRound`, `lipSpread`, `lowerLipContact`, `tongueVisible`) by interpolating provided `plan['controls']` samples. Without a plan it uses clearly identified synthetic motion, **not** narration timing. Passing the optional `--brand` path embeds the actual Rovor mark; the standard repo mark is auto-used when it exists beside the checkout. In an environment missing the official binary asset, a visibly labeled *unverified text placeholder* appears instead. Do not mark that placeholder as official artwork.

Usage from `evan-engine`:

```bash
python -m unittest -v test_cartoon_rig_blockout.py
python cartoon_rig_blockout.py /path/to/outputs/cartoon-blockout --fps 24 --frames 96 --speech-plan /path/to/speech-plan.json
# Omit --speech-plan to use only synthetic demonstration controls, never a real lip sync claim.
```

Requires Python 3, `cairosvg` and `ffmpeg` for renders; the SVG-only `frame_svg(t, plan)` is independent of those. Produces native-size PNG frames, **editable** frame SVGs, a ~4-second 24fps normal-speed MP4, and an ~8-second half-speed MP4 with a machine-readable manifest. None uses Moho.

## Tests and critical visual review

Six focused automated tests passed on this engineering branch, including independent SVG layers/joints, distinct hand poses, pose exposure normalization, continuous-control interpolation and rejection of invalid sample inputs. Normal and half-speed films were rendered locally at 1280×720 and duration-checked. Native-resolution key frames were inspected. Initial tests exposed malformed SVG, a doubled face/jaw border and black stroke-only fingers; those were corrected before this checkpoint. The revised point/open/explain frame sequence is mechanically readable, but the results remain **simplistic construction art**, without the approved design sheet's exact anatomy. Remaining visible defects: geometric face and arms, stiff elbows and hands, smooth cross-fades not true finger in-betweens, mouth shapes too generic for credible F/V and L, limited jaw squash, no secondary hair/tie timing. A test clip is not studio-quality acting.

## Next

1. Inspect `evan-character/cartoon-v1/source/design-sheet-v1.png`, `setup-v1.png` and `speech-poses-v2.png` at native size on the authorized local checkout; the GitHub text connector cannot decode binary image files. Compare proportion/color/lineweight and replace blockout shapes with matched registered source plates—not flattened reference crops.
2. Derive real handed finger silhouettes and honest wrist in-betweens, fix elbow and shoulder hidden overlaps, and refine face/jaw deformation including lip contact, teeth and tongue masks.
3. Run the separate `review_acoustic_flags.py` audit on the real speech-plan JSON and exact 16k WAV, inspect all 18 disputed regions and preserve unresolved outcomes. Do not trust count/coverage as accuracy.
4. Use actual narration to drive a 4–8-second staged shot with correct official brand mark, render 24/48fps normal and slow, inspect F/V/L and P closure, and conduct a full-resolution acting/continuity review.
5. Preserve `main`, V3/V4, updater/symlinks and native Moho projects; do not open or probe Moho unattended, merge or deploy. Continue commits on development branches only. Do not disable the existing automation: polished cartoon milestone is not ready.