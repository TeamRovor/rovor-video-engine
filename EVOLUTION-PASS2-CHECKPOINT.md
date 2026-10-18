# Evan evolution pass 2 — continue here

2026-10-17. Continues Draft PR #5 and the existing local `development/evan-timing-review` checkout. Preserve all earlier projects, main, V3/V4, approved updater and native Moho. No merge, deployment or unattended Moho operation.

## Implemented upgrades

1. **Alpha-aware artwork registration.** `register_body()` previously treated invisible RGB as image evidence, so transparent leg gaps could falsely reject a correctly placed repair. Both images now use a common matte; only opaque source regions, eroded away from edges, drive ECC. Randomizing all fully transparent source RGB cannot alter registration. The existing shoulder candidate registers at 0.9931 with near-identity scale; the neck repair registers at 0.9935.
2. **Bounded shoulder repair.** `build_body_cleanup.py` applies the registered shoulder drawing only in two small underarm regions. Original pixels outside the allowed patch regions remain identical. It does not replace the character with a newly generated full body.
3. **Neck repair that preserves the collar.** A blanket neck-alpha trim was visually rejected because it produced a notch. The final repair replaces only selected neck colors with registered neck art and preserves the original alpha/collar. Original torso art remains independently available.
4. **Actual wrist-joint attachment.** The independent hand and its forearm now share the anatomical wrist pivot, rather than rotating around the old palm pivot. Surface tests sample across the assembled join at several acting poses and reject transparent strips. Palette scales come from matching source-forearm and drawing-wrist sample patches.
5. **A third genuine hand drawing.** A registered relaxed/half-point drawing now supplies a breakdown between open and pointing, and on release. No hand-image dissolve is used. Point and relaxed drawings are preserved separately with registration metadata; transitions still need animator review.
6. **Less exaggerated F/V contact.** The new optional anatomy mode narrows and relaxes the original source-art contact, rather than using the rejected generated smile. The original F/V drawing remains intact. This reduces the frown-like aperture; it does not certify labiodental anatomy or phoneme timing.
7. **L tongue placement and occlusion.** The raised tongue is smaller and lifted toward the upper teeth, and composited behind the front teeth. Native comparisons show it stays within the mouth instead of reading as a protruding tongue. Bilabial closure remains pixel-identical to the original.
8. **Shared mouth-warp maps.** Cavity and teeth reuse their identical inverse mapping. A five-pose local benchmark took 3.194 s with independent rebuilding versus 2.411 s shared, with identical output pixels (24.5% less time in this small benchmark). This is not a claimed 24.5% improvement for the complete video pipeline.

9. **Decoded-video regression verification.** `verify_review_video.py` checks every decoded timestamp and frame, both native dimensions, 60 fps, audio-track start, and sample correlation against the original voice recording. Passthrough timestamps prevent FFmpeg from silently creating a regular cadence during verification. Shifted/mismatched audio and missing/repeated frames are covered by five additional tests. Each report identifies the tested video by SHA-256; this checks technical delivery, not acting or phoneme accuracy.

The new scene selects these experimental body/mouth options through `REVIEW_BODY_OPTIONS` in `cartoon_body.py`. The source-based body-cache fingerprint includes that module and the artwork bytes, so a real rig or art change gets a new cache while composition-only changes can reuse it. Default legacy head/body comparison paths remain available.

## Verification so far

40 rig/render tests and five decoded-video-verifier tests pass after the final code/art changes, covering repaired registration, bounded pixel changes, wrist surface continuity, full-take geometry, mouth occlusion, exact shared-map output, bilabial closure, recording matching and 1080p60 timing. Native before/after stills were inspected. Some shoulder fold/edge and neck-join roughness remain; this is not studio approval.

The complete original 22.047375-second recording has now rendered in both formats. Both files were fully decoded with timestamp passthrough: **1,323 frames each**, continuous timestamps, **1920×1080** / **1080×1920**, **60 fps**. Both audio tracks start at zero and decode to 22.047375 seconds, with **zero measured sample offset** and **0.999793** correlation against the original take at 16 kHz. Video duration is 22.05 seconds (the final partial audio frame is retained). Reports, including exact video SHA-256 identifiers, are in `review-evidence/evolution-pass2/`.

Intermediate directory: parent `work/full-take-evolution-v3`; source body frames remain fingerprinted under parent `work/body-cache`. Landscape/portrait composition stills were inspected at opening, hand release, middle and closing positions. Technical delivery passes; this does not certify artistic finish or phoneme timing.

## Continue without repeating work

- Do not rerun recognition/alignment, regenerate unchanged source sheets, or rebuild completed plates. The 18 earlier acoustic flags and evidence packets are preserved; no phone boundaries were changed in this pass.
- Do not retry the rejected generated F/V smile as if it were a new idea. The new F/V variant derives from the existing drawn contact.
- Keep the new registered repairs, hand drawings and caches. Refine remaining sleeve/neck edges and hand-pose timing using full-length moving evidence.
- Keep output at 1920×1080 / 1080×1920, 60 fps. Preserve voice assets locally; do not commit audio, video, body caches or private transfer data to GitHub.

## Recheck a completed preview

Run `evan-engine/verify_review_video.py VIDEO.mp4 ORIGINAL.wav --ffmpeg /absolute/path/to/ffmpeg --report report.json`, adding `--vertical` for portrait. The reference stays private and is not added to the repository. The verifier checks this full original take, rather than accepting a short clip as a completed delivery.

## Continuation — 2026-10-17 render-resume hardening (not a new art pass)

After the original nine upgrades, draft PR #5 gained one targeted reliability change without modifying source paintings, rig poses, phoneme timing, private voice files, or approved Mac updater:

- `evan-engine/chunk_integrity.py` decodes every frame of an existing chunk and checks native dimensions, expected frame count, and 60 fps. Missing, truncated, extra-frame, wrong-size, and wrong-rate outputs are not reused on resume.
- `render_acting_video.py` validates both formats before promoting newly encoded chunk files, and before skipping existing chunks. Completed final MP4 concatenations are now written to `.partial.mp4` files, then atomically renamed after successful encoding.
- `test_chunk_integrity.py` has five passing local unit tests. A separately encoded real H.264 three-frame sample also passed the gate, while a deliberately wrong expected frame count failed. These checks were performed in the chat's isolated test container, **not** on the Mac or the private original recording.
- Current draft PR head after these changes: `4e6691263aed51866368046789ccd2d3c81a783f`. No merge, deployment, narration re-alignment, or regenerated source art.

**Mac status at review:** the dedicated `rovor-video` self-hosted Mac runner succeeded in earlier GitHub Action sessions, including the read-only connection check. A later approved preflight run (GitHub Actions run `39073496099`) remains queued, so do not claim this new code has been executed on the Mac until a runner job actually finishes. Restart or reconnect the Mac runner to continue local FFmpeg/rig tests and artistic review.

**Next:** run the new five-test suite on the Mac, then the existing rig/render and full decoded-video verification tests. Inspect the open-to-relaxed-to-point hand transitions and remaining neck/sleeve contours on actual 60fps frame strips; static and structural passes are not artistic approval.
