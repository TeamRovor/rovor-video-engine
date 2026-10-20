# Evan Cartoon Engine — V3.1.1

An offline MP3-to-MP4 animation pipeline for Rovor Digital. It transcribes speech locally, times mouth shapes, selects illustrated topic scenes, animates Evan, adds captions, and exports a vertical video. It does not call paid AI services or use network APIs while rendering.

The renderer supports macOS and Windows. Both platforms need local FFmpeg, Whisper.cpp, Rhubarb, Node.js, Sharp, and a Whisper model. The source ZIP intentionally does not include executables, models, or `local_tools.json`.

## Configure local tools

Copy `local_tools.windows.example.json` to `local_tools.json` and edit the executable and model paths. `ffmpeg`, `node`, and other tools may be command names when they are on `PATH`; `model` must be a file path. `local_tools.json` is ignored by Git because it contains machine-specific paths.

Install the pinned Sharp dependency from this directory with `npm install`. Sharp 0.35.5 requires Node.js 20.9 or newer; see [Sharp installation requirements](https://sharp.pixelplumbing.com/install/#prerequisites).

To keep the configuration elsewhere, set `ROVOR_LOCAL_TOOLS_CONFIG` to its full path. The launcher and MCP adapter use the same setting.

## Windows

From PowerShell in this directory:

```powershell
..\install-on-windows.ps1
py -3 .\launch_evan.py --check
py -3 .\launch_evan.py "C:\path\to\narration.mp3"
```

The setup script keeps any existing config, installs the pinned Sharp package, and registers `rovor-evan-v3` if the Codex CLI is available. It does not install FFmpeg, Whisper.cpp, Rhubarb, or the Whisper model. Edit `local_tools.json` so the `whisper`, `model`, and `rhubarb` entries point to tools installed on your machine before running `--check`. You can also open `Make Evan Video.cmd` or drop an MP3 onto it. To use a path containing spaces, keep it in quotes when running the PowerShell command.

## macOS

Configure the same JSON keys with macOS tool paths, then run:

```bash
python3 launch_evan.py --check
python3 launch_evan.py '/absolute/path/to/narration.mp3'
```

Or open `Make Evan Video.command` and drop an MP3 into Terminal when prompted. The existing `install-on-mac.sh` can register the local `rovor-evan-v3` MCP adapter without replacing other MCP entries.

## Direct render and resume

```text
python animate_evan.py INPUT.mp3 --output NEW_OUTPUT_FOLDER
python launch_evan.py --resume EXISTING_OUTPUT_FOLDER
```

To provide a hand-authored scene plan:

```text
python animate_evan.py INPUT.mp3 --plan PLAN.json --output NEW_OUTPUT_FOLDER
```

The plan is a JSON array of scenes with `start`, `end`, `kind`, and `title`. Scenes must be ordered and cover the full recording. Available kinds: `browser`, `favicon`, `brand`, `social`, `store`, `search`, `contact`, `endcard`, and `topic`.

Resuming verifies the audio and scene-plan contents, character mode, engine version, tool configuration, and the resolved tool/model file metadata before reusing generated stages. Frame files are written atomically, so an interrupted frame is rendered again. Runs made before versioned fingerprints were added must use a new output folder.

## Limits

- Recordings are limited to 60 seconds.
- Scene selection is deterministic and keyword-based; review captions and scene choices before publishing.
- Captions from unusually long transcript segments are limited to three lines to stay inside the video frame.
- V3 uses reference-art pose swaps, not a native Moho skeletal rig. The V2 vector mode remains available with `--character vector`.
- Local stage timeouts are longer for transcription and encoding than for frame batches. Interrupted jobs can resume from completed work, but a local tool that repeatedly exceeds its stage budget still needs a faster model or shorter input.

