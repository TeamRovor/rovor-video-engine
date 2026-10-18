# October 18 — actual painter film V4, 132 seconds in both orientations

**Do NOT restart the Rovor painting film**. This checkpoint continues prior
V3 0–96s with newly authored animation 96–132s, sourced from the ORIGINAL
private user ElevenLabs audio. Keep all previous V3 review versions intact.

## Verified user-facing V4 review files

Location: private ChatGPT Library folder
`/Rovor Video Reviews/Rovor 4m23 Painting Film/`

- `First132s_Landscape_1080p60_ArtPassV4_REVIEW.mp4`
  1920×1080, 60 fps, **7,920 frames**, source narration [0,132).
  SHA256 `ae9d88300491d82f729db98e8c2e7f62f200a7c7cd4818e29787df2625ff41e4`.
- `First132s_Portrait_1080p60_ArtPassV4_REVIEW.mp4`
  independently staged portrait, 1080×1920, 60fps, **7,920 frames**.
  SHA256 `f554bbe019c91178ad43d603dcbbfb66774a7743aec1c03b5f6d1dafd911872d`.
- `First132s_ArtPassV4_Editable_Source.zip`: The full source code for the
  36-second new original scene animation, stitched final video code,
  QA tests, representative artwork keyframes and nested PREVIOUS V3 source.
  **This ZIP is the canonical V4 editable source**; do not reconstruct it
  from film screenshots. SHA256
  `49254e426bad4a1d30c4ba80dee826b848e6759d14de62cadfdb78b96965c342`.
- `First132s_ArtPassV4_Technical_QA.json`: full decoded PTS/voice data.
- `First132s_ArtPassV4_Keyframes.jpg`: visual proof; not studio approval.

These files were successfully saved to Library; in-chat sandbox links also
point to final outputs. Do not overwrite earlier reviewed V3 videos.

## New action sequence, source seconds [96,132)

- 96–104: A finished-room photo transitions into the original illustrated
  real painter process, making hidden behind-the-scenes work visible.
- 104–114: Painter prepares the room, physically draping a couch in
  animated protective cloth. A portrait occlusion bug was fixed:
  foreground furniture appropriately covers the painter's lower legs.
- 114–123: Painter inspects damaged plaster, then performs a
  hand/shoulder/elbow-linked putty knife repair close to the surface.
- 123–132: Rolling paint fills the repaired area; painter settles on
  the result rather than endlessly looping a generic talk-puppet pose.

This is custom original layer/motion code, not stock footage. The educational
painter is hypothetical and is NOT a real case-study customer. This does
not replace the original Evan character; source Evan appearance/rig remains
preserved in the existing project.

## Measured technical integrity, not artistic approval

Original private Oct 6 narration SHA256:
`346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`.

- Verified both [96,132) clips individually: exact 2160 frames each,
  60 fps PTS spacing, nine distributed original-audio comparisons per
  format all **>=0.999951**.
- Stitched V3 [0,96) and V4 [96,132) video-only streams to exact source
  frame boundary 5760 (96.000sec), then reencoded with ONE continuous
  original [0,132) narration AAC audio track. No patched or generated speech.
- Verified complete landscape and portrait independently: exactly 7,920
  decoded frames each; worst deviation of decoded frame PTS from
  frame_index/60 **3.34e-7 seconds**. Minimum voice correlation **0.999780**.
- Extra six seam-proximate voice comparisons at 63,64,65,95,96,97sec,
  each >=0.999968, no detected edit audio shift.
- Eight source/illustration motion smoke tests passed including SHA-locked
  narration, continuous movement across actions, independently staged
  portrait and landscape, and repaired-then-painted visual progression.
- Internal artwork generated at 960×540 / 540×960 and upscaled to
  1080p formats. Real video delivered at full-resolution output with 60fps,
  but **art is not native 1080 and is NOT feature-film quality**.

## Crucial unsolved items

The 2:12 review is **still an original illustrated motion blocking WIP**,
not a Hollywood-level cartoon. Painter construction remains relatively
simple, detailed gestures/facial acting and genuine surface contact
are still approximate; music and Foley are not mixed, words/phonemes
are not forced-aligned for the full audio, and shot timing is only an
editorial approximation. The ORIGINAL EVA NARRATOR is preserved and the
Rovor original painted rig has not been substituted or changed.

The full audio is 262.687313sec, so 130.687313sec (about 2:10.687)
still needs animated story coverage. The end narrates the Rovor brand as
reportedly "Rover Digital" and wrong spoken URL; verify and use a corrected
source take with the user's approval before release.

## Next steps

Continue from the editable V4 source ZIP and prior V3 scripts, NOT from
the older 96-sec v2 or 46-sec prototype. Improve original painter pose
sheets (expressive head, actual fingers/hands, anatomically connected elbow,
wall tool contact) and real story-specific compositions. Use accurate
narration word boundaries and artistic visual comedy when planning
[132,262.687), then render independently framed orientations with a single
continuous original voice track, check ALL frames/PTS and multiple voice
segments, and private-deliver. No paid tool, no publication, no main merge.

This checkpoint is metadata/continuity only. The video/scene code is in
the private Library V4 editable source, not committed in GitHub to avoid
unreviewed source duplication.
