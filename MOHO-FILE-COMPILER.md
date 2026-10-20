# Moho 14 file compiler

This compiler reads/writes the ZIP archive that contains `Project.mohoproj` JSON. It edits only identified bone or switch channels and writes a new `.moho` archive. It does not emulate Moho's complete data model: it currently accepts only the observed archive schema version 1038, requires project fps 60, frame origin 1, and an explicit 60-second maximum. Frame 0 is preserved as the setup pose. Use a new destination; existing files are never overwritten.

The source must already be a correct 60 fps project. The compiler refuses to rescale 24 fps animation: keys, actions, layer timing, audio, physics and reference channels all have time semantics, so changing just `project_data.fps` would be wrong. Frame sampling uses decimal arithmetic: `Moho frame = 1 + ceil(seconds * 60)`, while frame 0 remains setup. Thus 0.1s maps to frame 7 and 0.5s to frame 31. Exact boundary events occupy the frame beginning at that time.

## Inspect actual targets

```sh
python3 tools/moho_compile.py inspect /absolute/path/to/source.moho
```

Use the printed layer UUID, exact bone name and exact switch child names. The compiler will not infer `jaw`, eyebrow dials, viseme artwork, or any unobserved structure. Duplicate bone names in one target skeleton are rejected. This matters for the prepared disposable tutorial: it has generic `B1`… bone names and no approved Evan anatomy. Its source is a 24 fps file, so it remains unmodified by this 60 fps compiler.

## Patch format

Plan JSON keys are exact; `sourceSha256` must hash the complete input archive. One patch targets one channel. Animations on a targeted channel are replaced after explicit `replaceTargetAnimation: true`; unrelated archive members/channels are copied byte-for-byte and frame 0's value is retained.

```json
{
  "fps": 60,
  "sourceSha256": "<sha256 of source.moho>",
  "replaceTargetAnimation": true,
  "patches": [
    {
      "layerUuid": "<UUID from inspect>",
      "bone": "<exact existing bone name>",
      "channel": "anim_angle",
      "keys": [
        {"frame": 1, "value": 1.5707963267948966},
        {"frame": 31, "value": 1.7453292519943295}
      ]
    },
    {
      "layerUuid": "<switch layer UUID from inspect>",
      "channel": "switch_keys",
      "keys": [
        {"frame": 1, "value": "<exact child layer name>"}
      ]
    }
  ]
}
```

Supported bone channels are `anim_angle` (radians), `anim_pos` (`{"x":number,"y":number}`) and positive `anim_scale`. Switches use `switch_keys` and exact existing child layer names; interpolated switches are rejected. Validate and compile:

```sh
python3 tools/moho_compile.py compile /absolute/source.moho /absolute/plan.json /absolute/new-output.moho
```

The result says `compiled_pending_native_validation`; it is not rendered. Render to a separate folder with Moho Pro's command-line renderer. The installed Moho 14 executable accepts `-r`; the syntax for options follows the official renderer manual:

```sh
/Applications/Moho.app/Contents/MacOS/Moho \
  -r /absolute/new-output.moho -start 1 -end 60 -f png \
  -outfolder /absolute/render-frames
```

The command-line renderer's availability depends on a Pro license. The earlier probe accidentally confirmed an unsupported `--help` invocation aborts; use documented `-r`, not generic help switches. See Lost Marble's [command-line renderer manual](https://www.lostmarble.com/manual/13.5/Moho%20Users%20Manual.pdf) and [Moho 14.2 release notes](https://lostmarble.com/appcasts/Moho14.2Update.html) for command-line startup script support.

## Forced-aligned phone plan to switch keys

The `speech` subcommand consumes the existing JSON acoustic plan plus source-derived 16kHz mono PCM16 WAV duration, then runs `speech_plan_gate.py`. It rejects estimated/non-acoustic alignments and any unresolved flags. The rig mapping is a separate JSON object that the caller must calibrate from actual artwork and layer names:

```json
{"rest":"Rest", "phones":{"M":"MBP", "B":"MBP", "P":"MBP", "F":"FV", "V":"FV", "IY":"E"}}
```

That example is illustrative only. Every phone found in the plan requires an explicit mapping. No automatic English spelling conversion is performed. The emitted switch keys use exact 60 fps frame numbers, sample phone intervals on frame starts, and return to rest through gaps. Before compiling, confirm all returned child names exist on the exact switch layer; the archive compiler enforces this.

```sh
python3 tools/moho_compile.py speech /absolute/acoustic-plan.json /absolute/source.wav /absolute/rig-mouth-map.json
```

## Verified evidence and limits

A disposable `Project.mohoproj` archive at schema 1038 was inspected without editing the source. A separate diagnostic copy was made at 1920×1080/60fps, given a 60-key sinusoidal change on its existing tutorial bone, and compiled to a new archive. Moho Pro 14's installed CLI rendered all 60 frames in 3.574 seconds; all frames were 1920×1080 and 40 had distinct pixel hashes. A rendered frame differed from an independently rendered unpatched baseline. These are structural/native-render tests using the generic tutorial rig, not Evan, not a speech test, and not a visual-quality approval. A SHA-matched tutorial copy is in `~/Documents/Rovor/Moho-Connection-Sandbox/ROVOR_MCP_BONE_TEST_DISPOSABLE.moho`; its source is 24fps and no write was made to the live copy.

There is no headless JSON parsing claim for arbitrary future Moho versions. Native validation after compilation is required because a valid ZIP/JSON archive can still refer to missing external art, incompatible resource paths, or unsupported channel semantics. This compiler does not author rigs, smart-bone drivers, art, camera moves, storyboards, or soundtrack muxing. It does not yet take an uploaded MP3 through transcription, forced alignment and export. The original Evan rig, calibrated mouth layer mapping, real aligned sample, and ChatGPT-to-Mac authenticated upload/return connector remain separate blockers. Existing renderer QA and human production approval still apply.

Hosted CI runs only synthetic schema fixtures on Windows, macOS and Linux. Local verification used Python standard library and the installed Moho Pro 14 CLI on macOS; no uploaded recording or paid service was used.
