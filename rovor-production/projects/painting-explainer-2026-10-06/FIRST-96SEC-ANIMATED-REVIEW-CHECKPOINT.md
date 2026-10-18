# October 18: Actual first 96 seconds of Rovor painter film — two verified formats

Continue the existing painting explainer, user-provided original October 6 ElevenLabs voice,
rather than restarting or redoing the 46-second scene pass.

## New actual private video deliverables

All four files verified as present in ChatGPT Library:
`/Rovor Video Reviews/Rovor 4m23 Painting Film/`

- `First96s_Landscape_1080p60_MOTION_BLOCKING.mp4`:
  1920×1080, 60 fps, 5,760 decoded frames,
  SHA256 `f701a97b9862f69fa1827cba61c8e1bb0641bde5606a658424e40fcd79029a96`.
- `First96s_Portrait_1080p60_MOTION_BLOCKING.mp4`:
  independently staged 1080×1920, 60 fps, 5,760 decoded frames,
  SHA256 `f4e1453c78f6668163608790110e7fc791e51295d41ab67d7cc0f2004de8dd6d`.
- `First96s_Technical_QA.json`: technical checks including frame timestamp
  continuity and 13 original-audio comparison windows across the 96 seconds.
- `First96s_Editable_Render_Source_v2.zip`: reproducible existing first-46
  source and NEW second-50 screenplay blocking render + original SVG/PNG
  art, contact sheets and integrity scripts; excludes the actual private MP3.

Original MP3 SHA256 unchanged:
`346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`.

## New 46–96-second continuation

The original source narration is trimmed from 46.000 to 96.000 seconds,
NOT copied from another narration. The next 50 seconds use nine animated
blocking beats: the expert/buyer mismatch, hidden work and sofa protection,
the buyer's finished-photo/estimate viewpoint, project process website,
the experienced painter inspecting cracks, customer seeing blue walls,
different knowledge, educational process gallery, and a wall repair payoff.

There is a new simple, fully connected procedural painter shoulder/elbow/hand
motion with an object attached to its endpoint (roller). It is a hypothetical
educational cartoon; NOT a real customer, real job or replacement Evan.
It is NOT full rich character acting, detailed 2D background art, or verified
Evan phoneme articulation.

## Merging 0–46 and 46–96 without introducing AAC edit gaps

The first direct concat created a 23ms uniform video timestamp offset,
caught by full-frame PTS checks. FIXED by:
1. Remove audio from each already accepted H.264 part, preserving video.
2. Concatenate only the original two video bitstreams; at frame 2,760
   the second section starts at exactly 46.000 seconds.
3. Remux those 5,760 native 60fps H.264 frames with a SINGLE continuous
   original source voice AAC encoding over [0,96) seconds.
4. Verify both 1920x1080 and 1080x1920 results; every decoded frame matches
   frame_index/60 within 0.00035s.
5. Across both final outputs, the minimum tested original-voice agreement
   is >0.994. Each format passed 13 audio comparisons including either
   side of the 46-second seam.
6. Do not alter the original source MP3, any earlier verified preview,
   existing rig or main branch.

**No final editing/mixing/creative approval**: These are flat original
illustrated motion-blocking studies (720p and 720×1280 internal artwork,
upscaled to full-HD final video). Long-form phones, real facial acting,
studio-original backgrounds and final SFX/music are missing.

## Remaining 4:22.687 story

Completed source interval: [0,96). Remaining original source
narration: [96,262.687375) = 166.687375 seconds
(2min 46.687sec). No padded speech or invented footage.

For the next pass, reuse `First96s_Editable_Render_Source_v2.zip` and the
existing source art kit. Write a visually motivated next sequence anchored
to the original narration (the steps/protection/repairs/benefits, mechanic
analogy, responsive web interface, compare scope, truth and Rovor closing).
Prioritize new specific character acting and original art, not another flat
talking-head or scrolling slideshow. Measure precise word timing before
final artistic acceptance.

Important brand check: Original audio closing says "Rover Digital dot com"
according to user-supplied script; this must be audibly verified and corrected
with an approved new take before publication. DO NOT silently fabricate audio.

Source private Library files exist and were saved successfully. Main unmodified,
no new paid tools.
