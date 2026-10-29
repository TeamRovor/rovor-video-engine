# Painted Evan: first articulated narration shot

Latest: see PAINTED-EVAN-MOTION.md for the continuous-speech/48-fps revision requested after motion review. This document describes the first 24-fps milestone.

The user selected the **first painted visual-development board** derived only from the supplied real Evan photograph. This branch replaces the rejected geometric-mouth direction with new painted production plates and an opt-in source-art mesh renderer. The selected design is committed as `evan-character/painted-v1/source/approved-design.png`.

## What changed

- A new 1024×1536 setup pose with both arms/hands visible, plus a separately generated torso with hidden shoulder surfaces. Generated chroma plates are preserved unchanged; deterministic compositing mattes remove magenta without removing white teeth.
- Nine complete painted facial drawings, registered on the upper face. A second generated atlas corrects the excessive L tongue and improves FV contact. Hair, glasses and upper nose stay pixel-identical during speech.
- A facial landmark mesh deforms actual upper/lower lips, oral cavity, cheeks and chin into corresponding intermediate positions. This is **painted raster deformation**, not newly drawn vector lips. The first automatic optical-flow blend was rejected after native-size inspection showed doubled lip edges. No inpainted skin patch or procedurally drawn mouth is used.
- Each arm has hierarchical shoulder, elbow and wrist transforms with continuous skin weights. The hands move independently at the wrists, but there is only one open-hand drawing per side; fingers are not independently controlled. Left/right in the manifest mean the viewer's side.
- A 1920×1080, 14.8-second shot uses the earlier narration recording, its actual Rhubarb cues, authored asymmetric gesture tracks and head accents. One browser prop persists through the globe-to-favicon explanation. The exact official Rovor PNG appears in the header, tab and magnified detail. This is an authored lesson, not a claim of general automatic scene understanding.
- `animate_evan.py --character painted` selects the new Python renderer. Existing calibrated/reference/vector routes and the default remain unchanged. Unrecognized topics use a narration/title card instead of falsely showing a favicon demonstration. `--mouth-mode still` freezes the facial speech layer.
- PSD export creates and reopens a **12-pixel-layer** document: torso, two arms and nine registered head alternatives in named groups. Only neutral X is initially visible. The PSD is editable character art; the Python mesh controls live in code/manifest, not in Photoshop bones.

## Review evidence and current verdict

The full shot has 356 rendered frames. A serial pass took 170.25 seconds on this local CPU workflow, about 2.1 fps. The final camera revision rendered in two independent frame ranges taking 88.14 and 87.16 seconds. A complete sampled hand-geometry sweep across all 356 frames verified that both hands remain in the picture; sampled hand bounds are approximately x=43–1084 and y=811–1041. This is a workload measurement, not a controlled hardware benchmark or a finding that the Mac is inadequate. Frames have been inspected at 1920×1080 and facial transitions at native 418-pixel source resolution. A slow close-up is supplied for human playback review. No human perceptual approval is claimed.

The painted face preserves natural lip volume, teeth/tongue shading, stubble and cheek response substantially better than the rejected study. Closed-to-open transitions now have one corresponding lip contour. The separated upper-face drawing remains stable instead of changing hair/glasses on every phoneme. Elbow and wrist motion is visible while shoulders overlap the reconstructed torso.

**Development milestone, not production acceptance.** Remaining limitations:

- Small texture/color changes can still be seen between facial drawings; dense rapid speech and rounded-to-contact transitions need animator tuning. FV is improved but still deserves anatomical review.
- The head stays at one three-quarter angle. There is no true depth turn, gaze change or independent brow rig. Emotional acting is currently mainly head attitude and the speech drawings; approved smile/skeptical/concerned acting poses need integration.
- Open palms alone limit meaningful gestures. Finger/pointing/relaxed-hand drawings and stronger shoulder overlap are the next artwork tasks. Some sleeve contours retain a cutout appearance under larger rotations.
- The 418-pixel head plates support this medium shot. They are not 4K close-up facial masters. Fine hair edges still need final matte polish.
- A native Moho project/bone binding has not been verified. The IPC bridge timed out. A native command-line probe exited with SIGABRT during macOS application registration; the user reported Moho quitting and then confirmed they were only checking. No more native Moho launches are permitted in unattended work until the user explicitly reauthorizes them. Existing Moho files were not edited. This limitation is separate from the local renderer, which completed successfully.

Do not merge this into `main` as a finished release. A human animator's final acting/phonetic review and a character artist's cleanup remain appropriate before calling this production quality.

## Reproduce

Install optional packages into a dedicated environment:

```sh
python3 -m venv work/painted-env
work/painted-env/bin/pip install -r evan-engine/requirements-painted.txt
work/painted-env/bin/python evan-engine/build_painted_rig.py
work/painted-env/bin/python evan-engine/render_painted_scene.py evan-character/painted-v1/review-scene.json work/painted-frames 0 356 --budget 1800
work/painted-env/bin/python evan-engine/export_painted_psd.py --output work/Evan-Painted-Layers.psd
```

Use the same original narration recording for the review fixture; audio is deliberately not committed. The fixture contains its actual timed cues/segments. The render command alone does not synthesize audio. Normal MP3 use:

```sh
python3 evan-engine/animate_evan.py recording.mp3 --output work/painted-video --character painted --config /path/to/local_tools.json
```

The local tools config can set `painted_python` to the environment's Python and `painted_packages` to an optional package directory. Runtime dependencies are imported only by the opt-in worker. Fonts currently use macOS Arial paths.

## Validation

- All 40 tests pass with the optional painted dependencies installed. The inherited O/U exporter test was corrected to preserve distinct rounded sounds.
- New geometry checks cover zero-pose identity, hierarchy pivots and bone lengths, all 81 facial pose pairs at five interpolation fractions without triangle inversions, stable upper-face pixels, white-teeth alpha preservation and brief MBP closures.
- Backend-routing tests preserve the existing renderer and select the painted worker only explicitly.
- A separate 1.25-second input passed the complete existing MP3 pipeline, including Whisper, Rhubarb, rendering and encoding. It also exercised the generic non-favicon card.
- The PSD was saved, reopened, its 12 layers counted and its composite regenerated.
- The corrected camera framing was checked across all 356 sampled frame poses; both hands remain inside the image. The final 14.8-second H.264/AAC movie was decoded without errors. A 9.6-second silent quarter-speed native-resolution facial excerpt is available for human review.
- The standard system Python also passes the 40-test suite with nine optional artwork tests skipped, preserving the dependency-light default path.
- The original V3/V4 main checkout, approved release symlink and updater remain unchanged. No production merge or deployment is authorized.
