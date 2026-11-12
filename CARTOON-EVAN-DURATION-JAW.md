# Optional duration-sensitive jaw and independent contact teeth

The previous F/V correspondence fixes the doubled outer edge, but the100ms AE in “favicon” still drives a very large open jaw between two shallow contacts. `DurationCartoonHead` / `--duration-jaw` reduces short open-vowel excursion while preserving the recording, aligned phones and material/identity weights. It also gives the existing contact incisor layer an independent rigid child and source-derived aperture matte. This remains an optional study, not a release or the completed polished milestone.

## Duration and audio

The existing acoustic planner already weights C/D/E/F by the recording's10ms, seven-tap smoothed energy envelope. This pass retains that identity/energy signal. Only geometry from C/D OPEN VOWELS transfers toward the existing modest B geometry. Phone identity, A/G contact channels, tongue/material weights, resting X and rounded identities are not rewritten. Jaw/chin geometry intentionally changes; they still share a geometry vector.

The authored excursion multiplier is .45+.55*ease((duration-.08)/.14): at80ms or shorter .45, at220ms or longer1. The budget uses the same vowel onset/release envelope as the planner (.035s lead, .060s onset, .065s release) and normalizes overlapping vowel influences. Sustained vowels/fallback mode and exact pure pose controls remain available. This is cartoon undershoot, not measured speaker biomechanics, a rate/jerk guarantee or new forced alignment. The exact phone boundaries remain unverified. Audio-Phone-Jaw.png shows the original waveform, unchanged stored energy and geometry curves against the source phone regions.

## Contact tooth child

DentalFVCartoonHead extends CorrespondentFV and caches the actual fv-rig-v3 lip/teeth parts. The lip group follows the shared outer contour. Incisors retain their original uniform-plane thickness, translated by the difference between original/registered alpha-weighted X centroid and10%-mass upper-edge quantile. This uses continuous subpixel statistics rather than integer bounding-box jumps. A source-component support aperture (one native pixel of full margin, falling to0 at distance2) follows the lip field and clips moving teeth. The underlying generated dark underpaint remains visible where teeth are covered. No new source pixels/imagegen or whole-face patch.

The aperture is derived from the extracted component footprint including its small guard, NOT a separately drawn anatomical lower-lip inner edge or unseen dental reconstruction. The incisor layer contains a small boundary guard, and vowel teeth still mix with contact materials. Actual matte coverage changes are modest; the isolated tooth-only comparison is subtle. Do not describe this as solved tooth/lip anatomy. Unsupported tooth guides fall back to the existing registered contact. Existing compositor's default hook retains exact output at source414/422 after extraction.

## Evidence

13 targeted checks pass (five duration, four dental, four existing correspondence): all9 pure controls exact; bounded/monotone duration curve, preserved contacts/rest/normalization, reduced short-vowel excursion, long-vowel/fallback behavior, source matte support, translation anchor, synthetic geometric occlusion without uniform alpha fade and empty-guide fallback. Across489 scene samples168 geometry apertures change and contact-channel maximum difference is0. All34 mixed contacts use valid independent tooth surfaces without dental/FV/rounded fallback.

“Favicon” geometry aperture peak44.5197→28.1988px; maximum adjacent-frame step18.4898→9.0311px and maximum second difference24.3116→13.2528px. Whole first489frames peak44.5197→31.3198px; max step18.4898→9.7555px. Earlier phrase aperture curve is unchanged (peak31.3198, max step7.9465). These are native geometry diagnostics, not rendered-boundary measurements or perceived-smoothness acceptance. Contact material weights and source audio/timing remain unchanged.

Native512px before/after shots cover “a favicon”/pause (source8.375–9.375s) and “instead of your logo” (187/48–235/48s), plus branded1280x720 integration for the former. Each normal film has48frames with original audio; each muted quarter-speed film192frames at48fps. All six films decode cleanly; main/earlier reviews have18/7 dental samples respectively, no fallback. See outputs/evan-cartoon-duration-jaw for full-resolution selected frames, graph, audit and decoding evidence. No continuous playback/listening acceptance is claimed.

At416 the enormous intervening open pose is visibly moderated; the tooth-only difference is much less obvious at full-head size. Heavy lower lip, corner spurs, plain tooth strip and worm-like shared tongue drawing remain. The selected cartoon likeness/official branding are retained; source drawings still limit anatomy. CPU raster warping limits iteration/detail. A character artist/animator and revised lip/tongue drawings are needed for final performance approval. Passing checks and smaller control steps are not studio quality.

## Next bounded work

Review this curve across the full reference acting shot and earlier contacts before promoting any candidate. Duration undershoot can weaken a short stressed accent; judge prosody against the recording. Judge normal-speed intelligibility/character performance, not just charts. Then replace the shared tongue's awkward blade shape and strengthen independent lower-lip/inner aperture controls from artist-faithful drawings; do not regenerate a whole head as a shortcut. Independent chin response, eyes and neighboring fingers remain unfinished. Preserve all acoustic timing until waveform/spectrogram/listening evidence warrants a correction; all18 flagged word-anchor rows have VISUAL review only.

Main/V3/V4/updater/approved symlinks/native projects unchanged; no merge/deploy or unattended Moho. Full milestone incomplete; automation stays active.
