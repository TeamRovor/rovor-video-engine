# Rovor Painting Film V9B — Original mechanic analogy continuation

**Status: WIP review, neither studio-quality nor ready to publish.** Film 0–156.283333 seconds (frames [0,9377)) is technically continuous. Prior V7 movie and source are preserved. New art source interval [8688,9377), 689 frames = 11.483333s. Entire original recording is 262.687313 seconds. Remaining ~106.404 seconds is still uncovered.

**Source of truth:** exact original ElevenLabs narrator MP3 with SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45` from private Library. It is intentionally NOT included in this ZIP or GitHub. No audio was synthesized or content-modified (output audio is ordinary AAC encoding from source). The small mechanic and customer are hypothetical secondary educational illustrations, NOT real Rovor customers or substitutes for Evan's original layered appearance.

### Portable source

- `mechanic_story_v9.py`: editable native-SVG scene art for two independently composed views, split at original frame 9032. This code is the actual source for accepted experimental V9B clips; never rebuild from screenshots.
- `render_mechanic_v9.py`: actual original-narration 60fps FFmpeg encoder for frames 8688–9377. Set `ROVOR_ORIGINAL_MP3` to private original source before running. Outputs V9B-named files (refuses overwrite).
- `stitch_v9.py`: combines verified existing V7 review 0–8688 frames and new V9B inserts into separately named 9377-frame output, with a single continuous original narration track. Expects full V7 WIP videos in sibling `rovor_v7` directory. Refuses overwrite.
- `verify_v9.py`: independently decodes all video timestamps and measures multiple source-speech comparisons for each orientation, recording flagged correlations instead of concealing them.
- `contact_audit.py`: reusable standard-library-only mathematical pose-link auditor for future episodes; it is **not** a substitute for actual frame-by-frame artistic inspection.
- `test_mechanic_v9.py`, `test_contact_audit.py`: 19 passing tests on actual original audio hash, storyboard native SVGs and mathematically sampled pose data.
- `editable_svg/`: eight native vector scene keyframes, separated per scene and composition.
- `private_qa/`: actual decoded-video timing/audio JSON reports for inserts and full review, plus decoded-frame contact/cut sheets.
- `prior_acceptance/Rovor_Painting_Film_V7_Editable_Story_Source.zip`: original whole V7 editable history (V6/V5/V4 nested) preserved byte-for-byte.

### Repeatable commands (requires FFmpeg, Python 3, Pillow, Cairosvg, numpy, private original MP3 and prior V7 review MP4s)

```bash
export ROVOR_ORIGINAL_MP3='/private/path/to/exact_original.mp3'
python -m unittest -v test_mechanic_v9 test_contact_audit
python render_mechanic_v9.py
python render_mechanic_v9.py --portrait
python stitch_v9.py
python stitch_v9.py --portrait
python verify_v9.py First156p283s_Landscape_1080p60_V9_STORY_WIP.mp4 --full
python verify_v9.py First156p283s_Portrait_1080p60_V9_STORY_WIP.mp4 --full --portrait
```

The full outputs still contain simplistic older 0–144.8s scenes, and V9B itself does not yet meet the professional creative standard. Explicitly see `V9B-ART-DIRECTION-AND-REVIEW.md`. Word boundaries, lip sync, final original soundtrack, Rovor spoken outro and human creative approval remain unresolved. Leave draft PR #5 unmerged, preserve previous deliverables, do not spend money.