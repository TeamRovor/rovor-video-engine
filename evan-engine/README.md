# Evan Cartoon Engine — V3 Reference Art Edition (offline prototype)

An MP3-to-reference-faithful 2D cartoon pipeline for Rovor Digital. It uses locally installed Whisper, Rhubarb, Node/Sharp, and FFmpeg to transcribe a recording, time Evan's mouth shapes, choose *illustrated topic scenes*, animate his head/hands, add captions, and export an MP4. No paid AI APIs, network requests, stock video sources, or Moho launch.

Read `../START-HERE-V3.md` first; it explains the new reference sprites and optional vector mode.

## Mac: use it with one MP3

1. **Keep the existing Codex handoff workspace and its `work/` directory**; `local_tools.json` points to the installed local executables/model there. This ZIP does not duplicate those Mac-specific tools.
2. Put this whole `evan-engine` folder somewhere convenient next to `evan-character` (it doesn't need to overwrite your existing Moho project).
3. Double-click `Make Evan Video.command`, drag one **MP3** file into the Terminal window, and press Return.
4. The video will appear in the new, timestamped `evan-videos/` folder next to this engine folder. Earlier results are not replaced.

If macOS prevents the command file from opening because of permissions, run `chmod +x '/path/to/evan-engine/Make Evan Video.command'` **on the copied command file only**.

If the local-tool check says files are missing, inspect `local_tools.json` and update only the relevant paths to existing executables. Do **not** delete the original Codex `work/` folder.

## Advanced commands

Fresh render:

```bash
python3 animate_evan.py '/absolute/path/evan.mp3' --output '/absolute/path/NEW-result-directory'
```

Continue an interrupted render (same input, same result directory):

```bash
python3 launch_evan.py --resume '/absolute/path/existing-result-directory'
```

Provide your own scene plan rather than the local keyword-based storyboard:

```bash
python3 animate_evan.py '/absolute/path/evan.mp3' --plan '/absolute/path/my-scenes.json' --output '/absolute/path/NEW-result-directory'
```

The scene plan is a JSON array, e.g. for a **12-second recording**:

```json
[
  {"start":0,"end":4,"kind":"browser","title":"Your website"},
  {"start":4,"end":9,"kind":"favicon","title":"A favicon"},
  {"start":9,"end":12,"kind":"endcard","title":"Rovor Digital"}
]
```

Scenes must cover the full duration with no gaps. Available kinds: `browser`, `favicon`, `brand`, `social`, `store`, `search`, `contact`, `endcard`, `topic`.

## What's new in V2

- Automatic rule-based illustrated scene suggestions from transcript phrases.
- Phrase-driven pointing, presenting, small-detail, emphasis and outro gestures.
- Original SVG browser, favicon, branding, social, online store, search, inquiry and end-card scenes.
- A manually editable scene plan for exact direction.
- Output recovery with `--resume`; intermediate stages and completed frames are reused, and truncated JPEG frames are detected and repaired. Video output is written atomically.
- Ten local unit tests. `python3 -m unittest -v test_evan_engine.py` runs them without an API account.

The included `../evan-character/evan-storyboard-v2.mp4` is a **22-second verified example** derived from the original Evan favicon voice recording and synced captions. The `../evan-character/scene.json` shows its real timing, scenes, and gesture data. The additional `storyboard-preview.jpg` shows four distinct moments. The full recording was verified as 529 H.264 frames with AAC audio.

## Boundaries / current limitations

This is **not** a finished Moho rig or a frame-by-frame studio animation. The default V3 is a reference-faithful raster pose-switching puppet, not yet a native Moho skeletal rig; the old simplified vector rig remains as `--character vector`. Scene selection is **keyword-based, not deep semantic comprehension**, and can miss subtle phrases. It picks from nine purpose-built graphic categories instead of making arbitrary new art or selecting photos. Captions rely on local ASR and may require corrections. The 60-second recording cap and 28-second subprocess budget remain; some long or slow transcription requests may still time out. The resume path helps with interrupted rendering, but cannot force a local tool to run successfully if that tool itself repeatedly exceeds the limit.

Moho is **not** started, and the provided references and original video are left unchanged. The original Moho project and its AGENTS.md are not in this ZIP and have not been inspected in this chat.
