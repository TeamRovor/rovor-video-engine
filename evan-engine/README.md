# Rovor Digital Video Engine — V3.4.0

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

## Shared workspace and update awareness

Before starting a new task, check which code is installed and what other sessions are doing:

```text
python workspace_status.py
python workspace_status.py --fetch
```

On Windows, use `py -3`; on macOS, use `python3` if needed. The first command reads local Git state only. `--fetch` refreshes origin refs without pulling code, switching branches, changing working files, or installing anything. The report identifies the current commit, tracking branch, ahead/behind counts, local changes, and open task claims from fetched `origin/main`.

The MCP adapter exposes the same check through `evan_workspace_status`, with optional `fetch: true`. `evan_engine_status` also includes a cached workspace snapshot, even when render dependencies are missing. Restart an existing MCP server after pulling to discover the new tool.

A pending pull is reported separately from local modifications or diverged commits. Preserve active work before updating. A clean checkout that is only behind its intended tracking branch can use `git pull --ff-only`; the helper never runs that command. Shared claims must be recorded on main before work begins. Read the canonical `AGENTS.md`, `PROJECT-LOOP.md` and task queue before claiming work; the report is a snapshot rather than a task lock.

The helper requires a Git checkout to compare updates. A standalone ZIP install reports that comparison as unavailable. Without a successful fetch, remote information is explicitly labeled as cached.

## Direct render and resume

```text
python animate_evan.py INPUT.mp3 --output NEW_OUTPUT_FOLDER
python launch_evan.py --resume EXISTING_OUTPUT_FOLDER
```

## Review and correct captions

Once transcription and lip-sync are ready, the render folder includes an editable `captions.srt`. Correct its text or timings in any subtitle editor, save it, then run `python launch_evan.py --resume EXISTING_OUTPUT_FOLDER`. The engine reads the saved transcript and lip-sync data, redraws frames with the corrected captions, and replaces the MP4 only after the new render finishes. It does not rerun Whisper or Rhubarb for caption-only edits. The same SRT can be supplied explicitly with `--captions PATH_TO_FILE.srt`. Keep cues in start-time order and avoid overlap because the video shows one caption at a time.

The engine checkpoints completed frames and prevents two processes from writing to the same render folder at once. Changed captions or saved scene data invalidate the old frames and encoded video while leaving the existing MP4 in place until the replacement is ready. MCP polling continues to report a render as active while that replacement is being created.

The local MCP adapter can start renders with optional `captions_path`, `plan_path`, and `character` values. It returns the output `captions_file` path so you can edit subtitles, then continue the job with `evan_continue_render`; the adapter uses the saved tool configuration and render stages.

Each completed render writes `render_result.json` with the output settings, file size, caption and scene fingerprints, total active render time, and time spent in each local processing stage. Timing totals carry across resumed attempts; waiting between attempts is not counted. `evan_render_status` includes this report after completion. The report helps identify whether transcription, mouth timing, frame rendering, or video encoding is the slow step.

## Future Moho Pro bridge

`scene.json` is the handoff point for a future Moho adapter: it contains the timed transcript segments, mouth cues, scene plan, gestures, captions, and character style. A later adapter can translate that data for Moho Pro while the current local renderer remains usable on its own. This version does not launch or modify Moho.

To provide a hand-authored scene plan:

```text
python animate_evan.py INPUT.mp3 --plan PLAN.json --output NEW_OUTPUT_FOLDER
```

The plan is a JSON array of scenes with numeric `start` and `end` times, `kind`, and `title`. Scenes must be ordered and cover the full recording; every scene must start before the audio ends. Available kinds: `browser`, `favicon`, `brand`, `social`, `store`, `search`, `contact`, `endcard`, and `topic`.

Resuming verifies the audio and scene-plan contents, character mode, engine version, tool configuration, and the resolved tool/model file metadata before reusing generated stages. Frame files are written atomically, so an interrupted frame is rendered again. Runs made before versioned fingerprints were added must use a new output folder.

## Automated regression checks

```text
python -m unittest discover -p 'test_*.py' -v
```

The portable CI matrix checks Linux, Windows and macOS. Tests exercise real pipeline/resume decisions with synthetic external-process output: unchanged resume reuse, saved frame checkpoints, caption-only corrections, transcript/mouth invalidation, preservation of the prior video on encode failure, folder locks, Windows-style subtitle files, Unicode paths, and MCP status. Workspace checks use temporary local Git repositories to verify pending updates and divergent/local work without network access.

The workflow also installs the pinned Sharp dependency and runs `node --test test_renderer.cjs`. Those smoke checks draw and fully decode frames using the unchanged reference poses, rasterize the vector renderer, exercise caption escaping/wrapping, and run the frame subprocess for a tiny requested range. These are internal diagnostics, not a finished video.

The checks do not establish a successful full Whisper/Rhubarb/FFmpeg run, Evan's laptop readiness, or visual animation approval.

## Limits

- Current renderer output is 720×1280 at 24 fps; the 1080p60 production target remains separate work.
- Recordings are limited to 60 seconds.
- Scene selection is deterministic and keyword-based; review captions and scene choices before publishing.
- Captions from unusually long transcript segments are limited to three lines to stay inside the video frame.
- V3 uses reference-art pose swaps, not a native Moho skeletal rig. The V2 vector mode remains available with `--character vector`.
- Local stage timeouts are longer for transcription and encoding than for frame batches. Interrupted jobs can resume from completed work, but a local tool that repeatedly exceeds its stage budget still needs a faster model or shorter input.
