# Evan Engine V3 — Reference Art Edition

**State:** tested reference-image sprites and an offline frame renderer; no changes have been made to your Mac from this package. Version 2 remains independent.

## Why this version exists

The V2 cartoon drew Evan from rough vector paths and lost much of the approved reference look. V3 uses *actual cropped illustrations* from the supplied `evan-personality.png`, keeping the details of Evan's face, sunglasses, hair, navy shirt, black tie, and original artist shading. No generative recreation of Evan is used. Pose and mouth variations are taken from your two provided reference sheets. This makes the character visually more recognizable.

## What V3 can do

- Animate 3 authentic reference-art poses (neutral, pointing, explaining/open hands) in a 720×1280 vertical video.
- Use Rhubarb's real speech timing to switch between 9 extracted reference mouth shapes, instead of drawing a simplified vector face.
- Keep automatic keyword-based topic illustrations, synchronized subtitles, and video export from V2.
- Run entirely offline using the existing Codex `work/` executables already verified on your Mac: FFmpeg, Whisper, Rhubarb, Node, and Sharp. No pay-per-generation subscriptions.
- Preserve V2 vector mode via `--character vector` if a shot needs its bendable arms.
- Save intermediate stages and resume interrupted render jobs.

## Important, honest limitations

- These are **pose-based raster sprites**, *not* an editable Moho skeletal character rig. Arms change in pose swaps; they do not individually articulate yet.
- Visemes are cutouts blended onto the original drawings, not handcrafted Photoshop/Moho mouth replacements; occasional seams and expression inconsistencies remain possible.
- Topic illustrations are deterministic/rule-based, **not** AI-generated semantically perfect scenes; human quality review remains necessary.
- V3 does not automatically repair the independent Moho MCP timeout observed previously.
- Existing up-to-60-second audio restriction and local subprocess timeouts remain. Long-form videos require further engineering.

## Mac installation — new folder, no V2 overwrite

1. Download `Evan-Engine-V3-Reference-Art.zip` to **Downloads**, leaving it zipped.
2. Paste this entire block into **Terminal**:

```bash
mkdir -p "$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art"
ditto -x -k "$HOME/Downloads/Evan-Engine-V3-Reference-Art.zip" "$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art"
bash "$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art/install-on-mac.sh"
```

The installer checks the engine and local tools and registers **`rovor-evan-v3`** with Codex if Codex CLI is present; it deliberately leaves `rovor-evan-v2` and `moho-mcp` intact. You **do not** need Codex credits to run local Terminal video renders.

## Run your own MP3 in Terminal

```bash
python3 "$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art/evan-engine/launch_evan.py"
```

Drag your MP3 in when asked, then press Return. The output is under the new folder's `evan-videos/` subfolder.

### Low-level direct test

```bash
ROOT="$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art"
python3 "$ROOT/evan-engine/animate_evan.py" "$ROOT/evan-character/evan-original-extracted.mp3" --output "$ROOT/evan-videos/v3-first-local-test"
```

The above command uses the sample MP3 and the V3 **reference** pose mode by default. To run the old articulated vector character, add `--character vector` to a *new* output folder.

To resume a stopped render (same audio and same output):

```bash
python3 "$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art/evan-engine/launch_evan.py" --resume '/absolute/path/to/unfinished-render'
```

## Files for future Moho rig

- `evan-character/references/`: untouched originals.
- `evan-character/v3-assets/{neutral,point,present}.png`: transparent original-art pose cutouts.
- `evan-character/v3-assets/{neutral,point,present}_{rest,AE,O,UW,L,FV,MBP,smile,open}.png`: 27 prepared speech-mouth expression combinations.
- `evan-character/v3-assets/visemes/`: nine independent mouth sprites directly extracted from the reference rig sheet.
- `evan-character/v3-assets/{confident,amused,talking}.png`: portrait expression assets.
- `evan-character/v3-assets/asset-map.json`: documented source crop regions.

A true Moho rig would need **separate layer drawings** (head/hair/eyes/jaw/torso/upper arms/forearms/hands), proper masked joints, and bone/switch layers. This pack is a correct-art **reference** and a working pose-swap intermediate stage, not a substitute for those layers.

## Controls / quality

From `evan-engine/`, run `python3 -m unittest -v test_evan_engine.py`. This uses Python's standard library and is completely offline. Use `python3 launch_evan.py --check` to verify Mac tools. Inspect every rendered video for imperfect mouth swaps, captions, and mismatched illustrations before publishing.

The screenshot/contact sheet and MP4 demo provided separately are produced from the existing 22-second favicon recording in your original handoff.
