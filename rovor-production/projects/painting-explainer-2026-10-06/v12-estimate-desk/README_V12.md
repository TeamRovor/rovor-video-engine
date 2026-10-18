# V12 Reproducible Estimates Scene / Production Handoff

Project: Rovor Digital's original October 6, 2026 4:22.687s painting explainer.
**This is a separate review branch WIP, not film release approval.**

- Source recording: 262.687313s, private MP3 SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`. Original audio is NOT in this ZIP.
- Target patch: 29.2 to 41.4 seconds, frames 1752–2484 exclusive, 732 frames at 60fps.
- Continuity: V11's first 9377 frames preserved except the defined patch; full review duration remains 9377/60=156.283333s. 106.404 seconds remain unanimated.
- V12 uses an original illustrated tabletop, painter's estimate documents, cartoon forearms and stamp; portrait and landscape compositions are distinct. This is a hypothetical demonstration, not evidence of a real Rovor job.
- A stamp traveled instantly between positions in rejected V12A. The final V12 code interpolates it with a lifted hand and passes a real rendered-SVG pose continuity test, plus 16 other source tests.
- Verified actual MP4 exports (saved **separately** in private Review Library): native SVG rendered 1920x1080 / 1080x1920 at 60fps, 732-frame inserts and 9377-frame independently assembled full WIP copies. The full-film source voice preserves all 12 comparison windows to numerical equality with V11; low windows still require human listening. No exact spoken-word alignment has been approved.
- The 17 tests are not artistic approval. The artwork is still simple, especially finger anatomy, backgrounds, lighting, expressions and storytelling pace.

## Files

- `estimate_desk_v12.py` original editable SVG illustrations and frame-directed physical action.
- `render_v12.py` full-HD narration-locked dual-format insert rendering; needs `original.mp3` in working directory.
- `verify_v12.py` full decoded frame PTS + original-audio checks for insert/full video.
- `splice_verified_source.py` intact reusable exact-frame source-audio splicer from V11.
- `continuity_guard_v12.py` reusable pose teleportation and hand-prop contact guard.
- `test_estimate_desk_v12.py` and `test_continuity_guard_v12.py` regression suite.
- `compare_motion_v12.py` comparison against prior decoded footage (external V11 MP4 expected at local path).
- `editable_svg/*`: 12 editable SVG art key poses.
- `V12_*QA.json`: engineering evidence and voice A/B comparisons.
- `prior_acceptance/Rovor_Painting_Film_V11_Editable_Scene_Source.zip`: complete preexisting source archive, unmodified.

## Continue, don't restart

1. Use the `V11` previous version as the accepted technical baseline; do not overwrite it.
2. Compare narration at original 29–42s by listening and adjust timing of hand contact/stamps. Word boundaries currently rough.
3. If art is approved, use the verified review pair; otherwise refine original SVG and rerender *both* formats.
4. Keep developing meaningful new 2D scenes and recheck known low-motion sections. Preserve Evan's established design and don't impersonate or regenerate him.
5. Continue [156.283,262.687313) only with original narration and actual illustrated events. The ending's spoken 'Rover' vs official ROVOR branding still requires an owner-approved corrected take.
6. Keep PR #5 draft and `main` unchanged. Do not publish any WIP.