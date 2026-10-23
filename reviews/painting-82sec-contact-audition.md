# ROVOR painting-film scene 82 — original-source repair audition

**Status: technically valid 30-second dual-format auditions; creative release REJECTED.** This work is an isolated private production trial, not a new approved video-engine version or a finished 4:23 film.

## Real source provenance

- User's original 262.687313-second October 6 MP3: SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`. No narration regenerated or modified at source.
- Both parents were the original **V12** `First156p283s_{Landscape,Portrait}_1080p60_V12_ESTIMATES_WIP.mp4`, 9,377 original frames, kept unchanged.
- Authored code traced from V12 ZIP through nested V11/V9B/V7/V6/V5/V4 to `First96s_ArtDirectionV3_EDITABLE_SOURCE.zip`, exact `v3/render_painting_scene_v3.py` (source region 64–96 seconds). The original Evan reference PNG from that archive is untouched.
- Previous 82-second shot was not a native painter roller failure: the V3 `[81,87)` buyer-view scene hid the room behind an oversized isolated rectangle. The original `[87,96)` scene is a browser showing how work is explained.
- V18 wall/roller source prototype was inspected **but NOT inserted** because its rejected hand/arm art and the current voice/story context do not justify using it as a replacement.

## Changed clip and verified engineering

- Both audiences: source interval `[70.000,100.000)` = 1,800 exact frames at 60fps, preserving previous V12 video on `[70,81)` and `[87,100)` unchanged in visual content, replacing `[81,87)` with 360 newly rendered authored source-art frames.
- Intended edit: restore perspective room and character visibility, keep roller/wrist tracking in a single coordinate model, visibly accumulate paint on the original wall surface and never erase paint during return, and preserve a concise lower-third rather than hiding the story in a floating opaque rectangle.
- Landscape: 1920×1080, 1,800 frames, duration 30.000 seconds, first frame PTS=0, last PTS=29.983333; maximum per-frame PTS step error below 0.7 microseconds. Output SHA256 `0da62e137f358b49cf26ddcf5229277dae41150c0dcfd9f1849c50bf88de9e32`.
- Portrait: 1080×1920, 1,800 frames, same timing. Output SHA256 `b944be0c4fb775d2a3a28a24cde489d30bd0bf881b94f244d7d41ced698ab639`.
- Both retain the original audio segment: the original decoded 16 kHz mono `[70,100)` PCM has 480,000 samples, the reviewed AAC decode has 480,003 samples, and normalized source/review waveform correlation is 0.999964 (no model voice regeneration).
- No Mac access, Open Interpreter, Moho or Final Cut execution, hosted original-media CI, spend, or public media upload was involved. The local source, renders and contact sheets are private conversation artifacts.

## Manual creative review — reject as production art

The obstruction is genuinely removed, and the roller paint position is no longer an unregistered floating UI. But **the character is still a flat front-facing puppet with little weight shift, simplified hands and static face; surrounding website sequence still resembles panels; background staging and composition remain basic**. This does **not** achieve the user's requested entertaining polished animation. Furthermore the 81–87 beat occurs near the narration's website/gallery analogy, and there has been **no approved word-by-word audio timing check** that the new painting action belongs under those words. A better-looking contact study is not automatically a story-correct replacement.

**Do not splice these audition frames into a public final deliverable, auto-post them, or describe them as an approved V13/V19 upgrade.** The complete film remains only 156/263s animated. Keep previously verified V12 untouched.

## Next corrective action

1. Use the actual original audio to certify the spoken ideas at 77–89 seconds and choose story-appropriate blocking before making more art. A likely scene is the *painter showing only a polished website gallery*, with the room/process revealed through a physical interactive visual, not a disconnected giant UI panel or unrelated roller insert.
2. Rebuild the approved painter's layered anatomy and rig (shoulder/elbow/wrist, pelvis, gaze, hands) to match the high-quality established Evan look without replacing his original PNG. Demonstrate weight shifts, contact and purposeful acting rather than pose switching.
3. Make an original 30–50s 1080p60 **dual-view** scene with continuous, context-correct, artistically detailed events and the same source narration; visually inspect normal-speed playback. Require owner acceptance separately from video technical QA.

**Supporting files:** two 30s private MP4 auditions, edited scene source `painting_82_repair.py`, frame-accurate `render_audition.py`, `verify_audition.py`, `TECHNICAL_QA_V19_CONTACT_AUDITION.json`, contact-sheet JPGs. The original audio/source MP4/assets are excluded from any public code repository or bundle.