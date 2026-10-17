# Painted Evan: temporal continuity revision

The user accepted the paused drawing but reported chunky, glitchy lip sync and movement. This revision keeps the selected artwork and rebuilds the motion rather than generating another set of still images.

## Root causes addressed

The previous speech sampler restarted a previous-to-target tween at every Rhubarb boundary. Short exposures could end before that tween finished, so the next exposure started from an image the previous frame had never reached. MBP sounds additionally snapped straight to the closed drawing. Face blend values were quantized. The first mesh implementation also chose a single dominant oral-cavity drawing; crossing the dominance threshold could switch teeth/tongue texture abruptly.

The new sampler uses overlapping, anticipatory temporal kernels across neighbouring phonemes. Complete painted drawings move into one shared, continuously changing set of anatomical landmarks. Closures approach, briefly hold and release around the actual bilabial event instead of snapping at its start. Very short vowel detections are consolidated; FV and MBP contacts remain. Wide vowels use a restrained conversational range. Oral interiors blend continuously rather than switching a winner. Fine facial detail remains artist-painted.

The acting curves now use monotone cubic Hermite interpolation: a joint moves through a continuing directional gesture without stopping at every control key. Shoulder motion leads the elbow by 35 ms and wrist by 85 ms. Head follow-through and subtle whole-torso roll connect the limbs to the body. Camera placement uses a premultiplied subpixel affine composite instead of integer resize/position steps. This reduces shimmer and staircase movement around hair, cloth and hands.

## Frame rate and compatibility

The revised review film is rendered directly at 48 fps from these continuous functions. Its intermediate frames are new rig renders, not duplicated frames or post-process optical-flow interpolation. The temporal sampler also improves the 24-fps path; 48 fps alone is not the fix.

`animate_evan.py --character painted --fps 48` uses the same MP3 pipeline. The legacy renderer default stays calibrated/24 fps. Non-24 frame rates are rejected for legacy renderers rather than silently retiming audio. Resume fingerprints distinguish the painted renderer revision so old/new frames are not mixed accidentally. Existing legacy resume fingerprints remain unchanged. Generic narration acting also now accumulates active gestures: a later zero-valued gesture no longer erases a current gesture. Default painted framing uses the verified complete-hand composition.

## Validation and limits

- All 46 tests pass in the full dependency environment. New checks cover speech-weight continuity across boundaries, a smooth closure reaching its target, continuous gesture velocity through directional keys, oral-cavity continuity across a former dominance threshold, conversational jaw range and valid multi-pose anatomy.
- The complete 14.8-second revision contains 711 directly rendered frames at 48 fps. Four frame ranges took approximately 267–270 seconds each concurrently on this local CPU workflow.
- A separate input completed the full MP3 pipeline at 48 fps, including speech timing, rendering and encoding.
- Final H.264/AAC encode is 1920×1080 at 48 fps, 14.8 seconds; full decode passed without errors. The previous 24-fps film is preserved separately.
- A 3-second excerpt was rendered first. Successive native-resolution frame sequences were inspected before the full render. Normal/slow playback files are supplied for human judgement; no human perceptual approval is claimed.
- A frame-by-frame projected hand-geometry sweep covers all 711 poses of the revised film; sampled hand bounds remain inside 1920×1080.
- At the same 24-fps sample rate, maximum source lip-landmark step falls from about 25.0 to 19.1 pixels, and the 95th percentile from 14.0 to 9.8. At 48 fps those values are about 14.5 and 5.3 pixels per frame. These are geometric diagnostics, not a studio-quality score or a substitute for watching the result. Fast real closures can still move quickly.

The character remains a painted 2D mesh at one three-quarter head angle, with two open-hand drawings. Emotional facial acting, hand variants, finer contact anatomy and human animation review remain part of the next development work. Native Moho remains unverified and is not launched by this revision. Main, V3, V4 and the approved updater remain untouched.
