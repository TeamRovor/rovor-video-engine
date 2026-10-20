# Evan Engine V3.1 — Reference Art Edition

This package turns a short MP3 narration into a captioned vertical Evan animation. The renderer is local and offline after its tools and Whisper model are configured.

## Setup

See [`evan-engine/README.md`](evan-engine/README.md) for platform setup, dependency configuration, the PowerShell launcher, direct rendering, and resume instructions. The renderer now supports both macOS and Windows.

The ZIP includes the engine and character artwork. It does not include platform-specific executables, the Whisper model, or `local_tools.json`; configure those on the machine that will render.

## What V3 does

- Uses three pose-based raster illustrations and nine mouth shapes taken from the supplied reference art.
- Adds offline Whisper transcription, Rhubarb lip-sync, deterministic keyword scenes, and captions.
- Saves intermediate stages so interrupted renders can resume after checking that the input audio, scene plan, character mode, and tool configuration still match.
- Preserves the V2 vector style as an option with `--character vector`.

## Limits

- Recordings are limited to 60 seconds.
- Scene selection is keyword-based and captions may need review.
- The raster pose swaps are not a native Moho skeletal rig; arms do not articulate independently.
- The engine does not start Moho or edit Moho project files.

Review each rendered video for lip-sync, captions, and scene choices before publishing.

