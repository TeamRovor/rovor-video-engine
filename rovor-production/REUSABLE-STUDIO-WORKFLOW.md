# Rovor animation studio — reusable workflow v1 (Oct 18, 2026)

This document governs source continuity, not creative quality. Keep all original Evan layered art intact (dark tousled hair, sunglasses, navy shirt, black tie) and every user-approved source. Do not fabricate customers, fake case studies, replacement voices, lip-sync approvals, or film-length claims. Never commit private original recordings, full review movies, model caches, or account credentials to GitHub. Work only on draft development branches; `main` remains unchanged.

## Where the real project lives

- **Editable V7 scene code:** the verified canonical `Rovor_Painting_Film_V7_Editable_Story_Source.zip` in ChatGPT Library `/Rovor Video Reviews/Rovor 4m23 Painting Film/`, SHA256 `b24f3f0013c7fbe2c9d6519e8fd398ad530f7556f506b50ba04f8f88fbff567f`; contains the unchanged nested V6, V5 and V4 sources.
- **Original narration:** original October 6 private MP3, SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`, measured duration 262.687313 seconds. **Not in the source ZIP and not in GitHub.**
- **Review outputs:** V7 independently framed landscape 1920×1080 and portrait 1080×1920, 60 fps, 8,688 frames per view, total 144.8 seconds. Existing render files are saved separately in Library. The V7 source render scripts depend on correct local paths to the V6 source movie and original audio; they are not a one-click standalone pipeline.
- **New permanent code:** `continuity_ledger.py` + `painting-film-ledger.json`, reusable between titles. Real source/archives SHA-validated locally; all metadata-only claims remain visibly unverified for media presence.

## One repeatable cycle per video

1. **Source lock:** choose and privately store *one* original audio file; measure exact duration and SHA256; reject a different or modified recording. Record the correct brand name/outro before approval.
2. **Review script and plan shots:** listen to entire source; correct transcript, then align words and visemes with confidence flags. Use actions, actor motivation, visual humor and transitions, not just keyword-to-infographic slides.
3. **Inventory existing art:** reuse verified Evan rig, clean hand/face poses, assets, and scene systems. Every new drawing must be source-registered in an editable layered form, and copied into the next ZIP/rig release. The V7 painter/customer are hypothetical illustrative secondary characters, not clients.
4. **Produce one scene at a time:** choose clear start/end frames; animate true contact, anticipation, follow-through, believable anatomy, backgrounds and independent portrait staging. Review storyboard, real-time motion and selected full-resolution frames, not just technical QA.
5. **Render separate full-resolution views:** reuse real original narration, no voice approximation, no padded/looped footage; use contiguous source frames and single encoded narration in stitched full-length reviews.
6. **Verify media independently:** decode every video PTS/frame, compare audio source windows with measured offsets, inspect every cut and likely articulation/contact defect. Preserve prior accepted versions. Low AAC correlations remain flags; do not silently redefine thresholds.
7. **Record continuity:** update `painting-film-ledger.json` or a new project ledger with true revised frame coverage, each edit interval, and exact editable ZIP hash. Run ledger tests and check actual SHA archives when accessible. This prevents future assistants from confusing **review coverage** with **artistic completeness**.
8. **Human creative gate:** director checks entertainment, anatomy, motion, reading order, brand, lips, music/Foley and all audio. Technical passes **never** equal studio quality. Publish/merge only on actual user approval.
9. **Productize repeated fixes:** generalize a useful rig control, compositor, verified Foley trigger, scene API or regression before starting the next video, so each film makes the engine more capable. Track genuine reuse; do not claim speedups without measured render time / labor data.

## CLI — no media is modified by this ledger

Run standard-library-only checks from the directory containing `continuity_ledger.py`:

```bash
python -m unittest -v test_continuity_ledger
python continuity_ledger.py painting-film-ledger.json
# For real production source audit, verify *bytes*:
python continuity_ledger.py painting-film-ledger.json \
  --original-audio '/private/path/to/original.mp3' \
  --archive '/private/path/to/Rovor_Painting_Film_V7_Editable_Story_Source.zip' \
  --json-out '/private/reports/painting-v7-ledger-checked.json'
```

The first CLI form validates metadata and intentionally reports `source_hash_verified: false`, `technical_video_verified_from_media: false` and `artistic_approval: false`. The second audits real original source bytes and any supplied archive. **An archive is never called verified unless its actual supplied bytes were SHA-checked.** Unverified earlier archives remain in metadata only.

## For a new YouTube video

Copy the ledger JSON; create a NEW stable `project_id`; set the *new* narration's true duration, SHA256 and calculated `total_source_frames` (`ceil(duration*60)`), and keep both independent orientation targets. Create first revision `v1` with only the actual validated review interval `[0, endExclusiveFrame]`. Include each edited frame span, the ZIP filename and SHA256. Do **not** copy this painting film's narration or art/approval flags as proof that another video is complete. Future continuations append revision entries; never rewrite history. Use the source verified original Evan model with shot-specific acting, not a generated lookalike.

### Known remaining production blockers

- Painting film has [0,8688) frames in technical review, from original duration 262.687313s/15,762 frame positions; remaining 7,074 frame positions (~117.887s). All existing clips remain rough visual WIP.
- Latest V7 and older accepted render tools are still separated among canonical nested ZIPs. A fully self-contained generic shot renderer and reproducible dependency lockfile are **not** yet in GitHub.
- No user-approved word-level alignment, quality-approved hand anatomy/acting, polished camera animation, final sound mix or completed final 4:23 film exists.
- Outro pronunciation/URL may be wrong in the original recording; verify sound and request the user's corrected official take if needed. Do not silently alter voice.
- A separate **human approval and release signoff** process is needed when this WIP ledger reaches full coverage. Passing this bookkeeping module alone never authorizes publishing.