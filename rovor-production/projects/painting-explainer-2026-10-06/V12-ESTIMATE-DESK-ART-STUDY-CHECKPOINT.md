# Rovor Painting Film — V12 original-art estimate-desk study

**Continuation:** V11 verified [0,9377) frames remains immutable. Current overall film WIP still covers only 0–156.283333s from the original 262.687313s recording, and [156.283333,262.687313) remains unanimated. V12 rewrites ONLY source seconds [29.2,41.4), frames [1752,2484) = 732 frames. Source MP3 SHA256 `346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45`. Do not put source media in public GitHub.

## Art direction and editorial change

V11 29–41 seconds looked like motion-graphic panels with two estimate illustrations and identical quality badges. V12 instead stages *fictional educational illustrations* of a painter's workshop desk: papers are physically slid into view, a foreground hand guides them, a hand-held rubber stamp strikes each document with the same generic 'QUALITY WORK' / 'FREE ESTIMATES' promises, and a natural lifted tool travels between the pages. No Rovor client, testimonial or fake result is implied. Top-down studio-comic artwork includes illustrated oak desk, coffee cup, folded cloth, painter's pencil, paint tool, textured paper and contact shadows. Landscape uses side-by-side estimates; portrait uses a vertical two-paper composition. All art remains editable procedural SVG.

## Learning captured in reusable code

- The first pose test revealed a stamp teleport: source t=8.35 jumped instantaneously between documents. Rejected and corrected to a smooth raised-hand transition, tested over real authored SVG positions for every one of ~300 frames in the travel interval.
- `continuity_guard_v12.py` audits arbitrary pose tracks for jumps, missing sample frames and disconnected prop/hand anchors; tests include failing samples.
- Earlier V11 source-faithful frame splicer and full decoded-frame/audio verifier are retained. Neither metadata nor structural tests certify beautiful art.
- 17 small unit tests pass. Character anatomy / hands, lighting, staging, pace, realistic stamp geometry, lip-sync alignment and sound mixing still require human evaluation.

## Review limits and gate status

Actual native-sized SVG-rendered 1920x1080 / 1080x1920 videos, 60fps, if accepted by exact decoded-frame/audio QA. This is a candidate **work in progress**, not approved release art. It is a purposefully selected non-Evan secondary metaphor; Evan's original dark-tousled-hair, sunglasses, navy shirt and black tie rig remains unchanged.

**Audio limitations:** narration is trimmed from the exact original SHA-locked private Oct 6 file. Source-to-video AAC re-encoding can reduce raw waveform correlation; do not claim perfect pronunciation or word-level synchronization. Verify with listening before final.

**Reproducible source:** `estimate_desk_v12.py`, `render_v12.py`, `verify_v12.py`, `continuity_guard_v12.py`, `test_estimate_desk_v12.py`, `test_continuity_guard_v12.py`, `compare_motion_v12.py`, original V11 splice tool, QA JSONs and a nested copy of the *canonical* V11 source ZIP. The original private source narration is deliberately excluded.

**Do not merge PR #5 or publish. Do not overwrite V11.** Next: inspect and refine these estimates against actual audible 29–41 seconds, rebuild weak 0:25–0:40 compositional transitions, and then continue [156.283,262.687) with original story scenes.

## Verified media results (after art-revision B)

Both 12.2s V12 inserts have exactly **732 decoded frames**, format-specific dimensions and 60fps frame timestamps with maximum decoded PTS error 3.34e-7 seconds. Both integrated WIP movie copies have exactly **9,377** decoded frames at the same source frame timestamps, dimensions 1920x1080 / 1080x1920. Original narration source SHA remains unchanged; outputs contain AAC re-encodes only. 12 comparisons per full-format review gave precisely the SAME source correlation as the earlier V11 film (max delta 0.0 in sampled floats), even in preexisting low-correlation windows; minimum sampled window is ~0.86566 at original second 1.5. Zero claim of phonetic precision or approved sound.

The new scene's half-second grayscale motion score was not higher than V11 globally: an early audition of the first render found ~5.13 average interframe pixel change versus ~5.93 for V11. That metric is confounded by hard edits and does NOT establish performance quality. Artistic intent is more legible *physical manipulation*, not raw movement. Camera/hand animation remains minimal; faces are absent in this top-down scene and character design requires polish.

**Critical limitations:** Word-level voice timing remains approximate. The original full movie is still only 59.5% *covered*, not 59.5% artistically completed. Final sound effects, Foley, music, Rovor narration brand correction, detailed acting and grading remain outstanding. This revised estimates scene is a WIP candidate, not a studio-approved replacement. V11 remains in the Library unchanged. No merge, publication or new spending.