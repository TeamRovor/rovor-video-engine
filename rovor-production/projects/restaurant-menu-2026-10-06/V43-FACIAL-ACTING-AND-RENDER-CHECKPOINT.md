# Restaurant menu V4.3 — acting and in-world phone review (18 Oct 2026)

**Current status: finished technical review, NOT artistically approved or publication-ready.**

Continuation from V4.2 source/animation with original narration unchanged (SHA256 93304542dcb7b3421616428807ad62f17f3c82d99779f6babc351ace3414d991).

This revision retains:
- The *same* actual illustrated phone for all screens; website and PDF are animated inside the perspective-mapped display, no floating duplicate device.
- The authentic user-supplied vehicle/R Rovor logo; no generated brand substitute.
- Original MP3 and zero background music, no fabricated restaurant reviews.
- Existing four diner poses and original environment art; V4.2 remains accessible.

New:
- `acting_v43.py`: authored beat-timed short blinks plus subtle source-safe head attention/pose shifts.
- Eye region skin matte and 2D eyelid study in dedicated facial ROI. Early smeared-eye candidates were rejected.
- Four regression tests, including checks that face animations do not repaint the phone screen or mutate source cels.
- A complete new render of portrait and landscape 1080p/60fps 1,390 frames (~23.166667 seconds), with full decoded-video verification.
- Audio correlation with original at 16k is 0.9999865722670409, zero sample offset in both videos.

**Canonical editable V4.3 source bundle, verified MP4s, QA and storyboard:**
`/Rovor Video Reviews/Restaurant Menu Video/ROVOR_Restaurant_Menu_V4_3_Acting_And_Editable_Source.zip`
Separate portrait/landscape MP4s live in the same ChatGPT Library folder. Zip contains actual Python renderers `source/animate_v4.py`, `source/animate_v42.py`, `source/animate_v43.py`, `source/acting_v43.py`, untouched exact logo and narration, artist references, rendered files, verifier and tests.

**Creative limitation:** This is still based on four flattened paintings and procedural facial overlays, not a proper hand-drawn layered animation rig. More pose keys, corrected hand grasp/arm acting, facial expression designs, and reframed readable phone UI are necessary before studio-grade claims. Review at normal playback and refuse quality promotion on QA numbers alone.

Keep draft PR #5 open. No merge/deployment/publishing authorized by this checkpoint.