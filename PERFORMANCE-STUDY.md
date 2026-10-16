# Evan performance study — review milestone, 2026-10-16

**Visual verdict: FAIL for production. Do not merge into main or deploy.**

This opt-in study builds on `experiment/moho-native-rig` at `7ce19f1`. It does not alter the installed renderer, V3 (`4e099b5`), V4 (`27b664b9`), the approved-release symlink, or the six-hour approved-sync job. That job reads only GitHub `main`; development branches cannot become active through it. The existing draft PR #2 remains a foundation, not a verified native Moho rig.

## Concrete change

`evan-engine/performance_study.py` exports a four-layer present-pose character: source-art torso, head, and two arms with independent shoulder pivots. Nine editable SVG mouth studies share outer contour topology. Lips change continuously between cue targets while a restrained displacement moves chin/beard texture with jaw opening. Brief MBP closures reach their complete target immediately. Head and shoulder accents use authored anticipation/overshoot/settling keys rather than continuous sinusoidal drift. The official Rovor PNG is used unchanged in the header and in the narration's website-identity demonstration.

These are **limited raster pivots plus experimental mouth vectors**, not a production bone rig. Arms have no separate elbows or wrists. No new eye, cheek or brow expressions are supplied. SVG topology alone does not verify Moho import/interpolation. G/FV and H/L require anatomically distinct artist drawings; aperture changes alone do not solve them.

A source defect was found during full-size review: some original white teeth pixels have zero alpha, apparently from the prior background-removal step. Replacing RGB alone leaves sparkling holes. This study fills alpha as well as color inside the local lip bed. It does not modify the original source PNGs.

## Review shots and critical comparison

The 6.34-second spoken study says: “A small mark helps people recognize your website. Keep that identity consistent, wherever they find you.” Narration is the Mac Samantha voice, not a proposed final performance. Rhubarb analyzed the actual recording. The cue fixture is committed, with its local audio path removed.

V3, V4 and the study use the **same present pose, camera size, background, cue timings and narration**. Baselines reproduce each released branch's mouth mapping against its original sprite assets. This isolates the face/control change; it is not an end-to-end comparison of the released scene directors. V3 uses its original mapping, V4 its default subtle mapping, including suppressed C/G/H sounds. The draft branch already fixes those mappings; that correction predates this milestone.

The review film puts three 1080×1920 panels side by side without reducing their pixels (3240×1920 total). The comparison PNG uses native 1:1 face crops. Inspect the original-sized assets, not a chat thumbnail.

Observed at full-size frame/crop inspection:

- V3: teeth/transparency noise, mismatched lip registration, and rigid face.
- V4: several distinct phonemes collapse to the original smile/rest; original skin detail is often better preserved than in this study.
- Study: independent head/arm timing and actual closed/open/rounded transitions are visible. Removed transparent-teeth residue no longer sparkles in the cleaned area. However, the lips are too geometric, their corners and thickness are insufficiently designed, and the harmonic skin fill softens the philtrum/cheek shading. It does **not** establish an artist-faithful face. Narrow overlaps also constrain shoulder travel and can leave doubled edges. Facial acting remains inadequate.
- Scene: the exact Rovor mark transfers into a browser-tab identity example around the website phrase, followed by a consistency connection. This is a simple authored demonstration, not a general narration-understanding system.

The review film plays the three-panel comparison once at normal speed, then at quarter speed. Frame inspection here is not a claim of human perceptual playback approval. No quality score or passing unit test overrides the visual failures above.

## Reproduce on this Mac

Requires Python with Pillow and NumPy, macOS Arial fonts, Rhubarb and FFmpeg. No generative replacement artwork or network rendering is used.

```sh
say -v Samantha -o narration.aiff 'A small mark helps people recognize your website. Keep that identity consistent, wherever they find you.'
ffmpeg -y -i narration.aiff -ar 16000 -ac 1 narration.wav
rhubarb -f json -o cues.json narration.wav
python3 evan-engine/performance_study.py --cues cues.json --output work/study --duration 6.34 --frames
# Repeat with --baseline v3 / --baseline v4 and different output folders.
ffmpeg -framerate 24 -i work/study/frames/%06d.jpg -i narration.wav -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest study.mp4
python3 -m unittest discover -s evan-engine -p 'test*.py'
```

The committed `evan-character/performance-rig` is reproducible from `v3-assets/present.png`; it is a review input, not an approved asset replacement. The script deliberately has no production-renderer integration. The new tests check fast closure preservation, authored timing holds/settles, source hashes, exported shapes and alpha repair. An inherited stale Moho exporter test was corrected to require separate O and U exposures. The exporter itself was not changed.

## What is needed next

A character artist/2D rigger should redraw a clean, layered 3/4 master based on the original sheet: intact facial skin, upper/lower lips, teeth, tongue, chin/cheeks, brows, neck overlap, torso under both shoulders, upper/lower arms and interchangeable hands. Approve neutral, skeptical, amused and emphatic face poses before rigging turnarounds. Use compatible vector lips with proper FV contact and L tongue placement. A human animator should tune phonetic accents, holds, hand arcs and facial acting against the actual narration.

The 408×524 present-pose crop cannot provide native 1080-detail character artwork. Supersampling changes edge smoothness, not source detail. The final study rendered 153 frames in 84.9 seconds (about 1.8 frames/second); the matched sprite baselines took about 20 seconds each while running concurrently. These are workload timings, not a controlled hardware benchmark. This local Pillow renderer runs on CPU and is an offline study; no GPU benchmark or hardware inadequacy is inferred. The Moho preflight call timed out, so no native .moho import, bone binding, interpolation or Moho render has been verified. Faster hardware would not repair the missing anatomy or art direction.
