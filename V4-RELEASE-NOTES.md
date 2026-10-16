# Evan Engine V4 — reference-art polish and real branding

Built from the Evan Engine V3 source package committed as `TeamRovor/rovor-video-engine` main (initial V3 code and user-supplied character artwork). The V4 installer creates a separate Git worktree and `feature/evan-v4` branch so V3's working files and `rovor-evan-v3` MCP registration do not change.

## Implemented

- **Original Rovor Digital logo.** Extracted an antialiased transparent black/white logo from the approved `rovordigital.png` source. The exact rover-shaped R appears in the header, favicon demonstration, branding graphic, and end card; removed placeholder R glyphs.
- **New mouth shapes for 3 reference poses.** Generated 27 calibrated PNG frames from original pose art and source visemes. Changed rest/closed sounds to keep the original unmodified face and rotated/resized the open shapes separately for each pose. Original V3 frames are untouched.
- **Subtle lip animation by default.** Prioritizes legible, natural-looking speech over exaggerated phoneme shapes. CLI provides `--mouth-mode detailed` and `--mouth-mode still` for experimentation.
- **Narration-guided scenes.** Added mobile design, page speed, website security, and analytics illustrations, only triggered by explicit transcript cues. No fabricated customer success stories or fake traffic statistics.
- **Longer inputs.** Removed the former 60-second ceiling, raised local processing subprocess timeout, and set an explicit 15-minute maximum. Long output is slower and may consume considerable disk space; no 5–10-minute audio was tested in this release.
- **Regression coverage.** 18 Python unit tests, plus a 530-frame video render and MP4/audio validation in the test environment.

## Limitations

- **This is not a native Moho bone rig.** It is a reference-art raster renderer. Three full-body pose variations remain, with hard pose cuts. The mouth has been improved but may still need manual artistic calibration.
- A code-based scene planner can only choose among illustrated subjects it knows; it is not a semantic video generator. More content packs and user-provided storyboards are needed for broad narration.
- The sample demo render reused the already generated Whisper/Rhubarb timing from V3. New-MP3 transcription and lip-sync need to be verified on the user's Mac after applying the patch.
- The full render uses substantial CPU time and temporary JPEG storage. Keep free space available.
- The separate Moho MCP bridge is not modified or tested by this release.

## Run on Mac

1. Download `Evan-Engine-V4-Patch.zip` to Downloads.
2. Unzip it to a directory in Downloads, then run `bash <extracted-folder>/install-v4-on-mac.sh`.
3. The installer creates `~/Documents/Rovor/Evan-Engine-V4-Development`, registers `rovor-evan-v4` when Codex CLI is present, and pushes a `feature/evan-v4` branch to GitHub (SSH authentication may ask for your key passphrase).
4. The previous `~/Documents/Rovor/Evan-Engine-V3-Reference-Art` directory and MCP remain unchanged. Review V4 branch before merging it into main.

## Local CLI options

```
python3 animate_evan.py /path/to/evan.mp3 --output /path/to/render
python3 animate_evan.py /path/to/evan.mp3 --output /path/to/render --mouth-mode still
python3 animate_evan.py /path/to/evan.mp3 --output /path/to/render --mouth-mode detailed
python3 animate_evan.py /path/to/evan.mp3 --output /path/to/render --character reference
```

V4 default is `--character calibrated --mouth-mode subtle`.
