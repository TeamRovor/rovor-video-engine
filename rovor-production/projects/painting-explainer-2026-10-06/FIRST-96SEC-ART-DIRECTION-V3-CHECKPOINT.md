# Painting film, art-direction V3: revised 64–96 seconds and new complete 96-second reviews

Checkpoint date: October 18, 2026. Continue **draft PR #5**; never restart from scratch. No `main` changes.

## Real deliverables created

The prior 96-second motion-blocking video is **preserved**. A new distinct revision replaces just the weak [64,96)-second stretch with an original illustrated full-room sequence, physically connected worker shoulder/elbow/wrist/roller, a wall-damage inspection, the customer paint swatch, and a transformation into service process illustration. Original Evan source character art is preserved; no generic substitute Evan produced.

Two NEW 96-second playable reviews, both independently staged at 60 fps:
- `/Rovor Video Reviews/Rovor 4m23 Painting Film/First96s_Landscape_1080p60_ArtDirectionV3_REVIEW.mp4`
  SHA256 `d3daae98d2cc20a8750e133bdfc3f7fd3e4eb76740e061110e1213a94dfc0e47`.
- `/Rovor Video Reviews/Rovor 4m23 Painting Film/First96s_Portrait_1080p60_ArtDirectionV3_REVIEW.mp4`
  SHA256 `0fe34e83fc4318ea3293e6ccedd9ee398cd36dcfef23c6f44f8459299dbef0ba`.

Both also saved as files in this chat's working attachments. Private ChatGPT Library folder also holds:
- `First96s_ArtDirectionV3_Editable_Source.zip`
- `First96s_ArtDirectionV3_Technical_QA.json`
- `First96s_ArtDirectionV3_Before_After.jpg`

### Technical verification

- Original ElevenLabs full 4:22.687 source MP3 unchanged (SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`).
- Renders include 0–64 seconds of original previous 96s video + NEW [64,96) visual section. Full 96-second soundtrack was encoded once from the **same original** voice file, avoiding per-chapter AAC seams.
- Each final orientation decoded as exactly 5,760 frames, 1920×1080 or 1080×1920, 60 fps; maximum deviation between decoded PTS and frame_index/60 = 0.0000003 seconds.
- 15 separated narration correlation checks from beginning to 94 seconds, including before and after the 64-second visual edit. Worst `0.994252` in each video; no source alteration.
- The source-only new [64,96) video is exactly 1,920 frames per orientation with eight correlation checks each all ≥0.99997.
- Earlier accepted previews remain intact for side-by-side comparison.

### What these do NOT prove

This is a **work-in-progress illustration-blocking upgrade**, NOT finished Hollywood/studio-quality animation. The painter is still shape-based, without polished expressions/secondary motion or believable painter/prop rig in every shot. The underlying artwork rendered at 1280×720 and 720×1280 then upscale to full-HD; native 1080 source artwork is unfinished. Evan original appearance stays intact but his face is not synchronized to speech in these revised scenes; full word/phoneme correctness, music/SFX artistic mixing, studio approval, and remaining 166.687 seconds of the film remain open.

### Reproduction

Private Library `First96s_ArtDirectionV3_Editable_Source.zip` includes the new director's Python motion renderer, stitching and verification scripts, original preserved Evan reference portrait and input manifest. Original voice MP3 is intentionally NOT bundled in the ZIP (not uploaded to GitHub); retrieve from user's actual conversation/authorized private files before rerender. Requirements: FFmpeg, FFprobe, Pillow, NumPy, Inter installed via system, zero new paid services. Do not upload private audio to repo.

The *next* meaningful quality work is NOT another repeated title-card style: draw original painter pose sheets and facial expressions/occlusion-ready backgrounds; develop narrative-specific foreground prop interactions and precise word-aligned scene timing, then revise actual quality in playable video. Remaining source [96,262.687) needs new original animation, not padding. The original narrator's closing brand/URL pronunciation must be checked against intended `Rovor Digital / rovordigital.com` before publication.

No source/graphics/main modification outside this draft project; no paid dependencies.
