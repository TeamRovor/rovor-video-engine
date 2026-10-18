# Rovor Digital — Painting Film V7, scope comparison (source 132–144.8s)

## Confirmed working files

Original film: 4:22.687313, exact authentic October 6 ElevenLabs audio SHA-256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`. Original recording **not included** in this ZIP. All previous original Evan artwork/rig remains unchanged. New character appearances are **hypothetical educational painter and customer**. They are not real customers, not case studies and not evidence of Rovor client results.

The new V7 illustrated segment spans exactly source `[132.000,144.800)` = 768 frames. It is original vector work, independently composed at 1920x1080 and 1080x1920 at 60fps, and accompanies original source audio cut from this range. The full WIP review spans source `[0,144.800)` = 8,688 frames at 60fps. Both are playable videos and saved separately from previous V6/V4 video versions.

Shot 1 (`132.000–134.880`): in-room painter and buyer physically consult a clipboard, with hands tied to the same prop.
Shot 2 (`134.880–139.830`): physical tabletop comparison of two illustrative estimates with different included scopes. Neither contractor is declared better.
Shot 3 (`139.830–144.800`): a paper flap moves away, allowing the practical included services to become readable.

The original 45-shot director timings were *rough*, not acoustically word-aligned. V7 uses those semantic beats as provisional editorial guidance. No full English transcription or phoneme analysis is certified for this take. This is **not a studio-approved cartoon** and the art still has simplified expressions, hand geometry, and stage lighting, and lacks bespoke Foley/music. Earlier scenes remain motion-blocking, despite 1080p60 final output. Do not label V7 final, publish, or merge into `main`.

## Rebuild

Keep the V6 reviewed 132-second movie files in a separate parent folder and preserve all older versions. You need Python 3, Pillow, CairoSVG, NumPy, FFmpeg and FFprobe. Supply the *exact original private MP3* using `ROVOR_ORIGINAL_MP3=/path/to/your.mp3` environment variable. The hash gate rejects the wrong recording. To assemble the full V7 review set `ROVOR_V6_DIR=/path/to/older/v6/files`. No source audio is committed to GitHub.

`python -m unittest test_v7 -v` verifies source, interval, SVG validity, custom shot composition, spatial animation, and image change.

`python render_v7.py` and `python render_v7.py --portrait` generate the 12.8-second scenes. They reject accidental overwriting. The full 144.8-second review is assembled with `python stitch_v7.py` and `python stitch_v7.py --portrait` using ONE continuously encoded original voice track rather than concatenating AAC chunks.

Run `python verify_v7.py <movie.mp4> [--portrait] [--full]` to decode check all video PTS and 9–12 original-voice windows. The verifier deliberately reports weak AAC comparison regions: no voice-analysis result constitutes artistic approval or word-level alignment. Inspect the original spoken words and adapt cut timing before final release.

## Source package

- `quote_story_v7.py`: all custom SVG art, character performance, stages, shot directing, prop drawing, independently framed portrait/landscape, native SVG frame output.
- `render_v7.py`, `stitch_v7.py`, `verify_v7.py`, `test_v7.py`: rebuild and test utilities.
- `keyframes/`: six actual native editable source SVGs, shot examples across both formats.
- `proof/`: V7 contact sheet, decoded splice inspection, complete QA JSON and render manifests.
- `prior_acceptance/Rovor_Painting_Film_V6_Editable_Vector_Art_Source.zip`: exact prior V6 source kit included intact; nested prior V5/V4 continuity. **Never reconstruct earlier accepted art from screenshots.**

## Next honest milestones

1. Review source narration syllables and word boundaries around `[129.9,150)` with actual listening and correct the semantic cut timing.
2. Refine human-looking hand/elbow anatomy, pupils, emotional interaction, perspective, painter expressions and foreground contact; current artwork still mechanical.
3. Continue `[144.8,262.687313)` mechanic analogy, responsive-web demo, fair quote comparison and original Rovor brand closing using original source/rig. 117.887313 seconds remain.
4. Verify whether the original outro says “Rover Digital” and an incorrect URL. Get a user-approved corrected ElevenLabs take if necessary; do not silently fabricate words.
5. Complete real audio/visual review, sound effects and music when they enhance visible actions; keep the original narration intelligible.