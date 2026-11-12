# Evan: continuous lower-arch correspondence and painted skin underlap

The review jaw can now follow the existing complete oral contour instead of collapsing it into a center/corner reconstruction or the rejected two-pose release adapter. This preserves intermediate curve controls, mouth width and the independently driven chin. It is a bounded development improvement, not polished character animation.

## Implementation and scope

contour_target_mesh in guided_jaw_exposure.py samples all nine lower-arch control points onto the existing source jaw guide, preserving the original horizontal/independent-chin falloff. No two-pose normalization, clipping or new temporal filtering. Invalid/nonfinite/unordered arches and inverted meshes reject. The existing target_mesh path remains the default; common triangle validation now also rejects nonfinite targets. Its valid output is unchanged.

CurrentContactExposure extracts its existing assembly into assemble_target so the review can reuse the same source correspondence, coverage guards and layers. It also accepts an actual optional skin-underlap plane, below the cavity and jaw. No default profile/config/export/updater changes. Callers are the new review renderer and focused tests; existing regression callers continue the original path.

render_contour_jaw.py compares legacy reconstruction versus lower-arch correspondence using IDENTICAL original voice, phoneme controls, source jaw and skin underlap on both sides. It reuses the existing continuously articulated head, including current F/V, teeth and tongue paths. The older six-plane contact study and failed two-pose voiced experiment remain unchanged. This comparison is a five-plane review exposure; mouth subparts still share its upper-face carrier. It does NOT complete independent lower-lip pressure or a fully separated face rig.

## Iteration on an actual defect

The first full contour attempt exposed partial transparency where the two antialiased attachment edges met: sampled oral-region minima175–202,42–76pixels below240. A matched edge position alone does not create an opaque joint. Initial films/audits/native pilots remain in outputs/evan-cartoon-contour-jaw/Rejected-No-Skin-Underlap. One unbacked frame919 also had one alpha-level difference at314,276; the review records it rather than claiming exact identity.

The fix places existing posed drawn clean-face skin underneath the cavity/jaw attachment. Its interior native box is190,305..285,365, entirely inside the face; source paint/alpha are unchanged. This is actual material underlap, with cavity and jaw still in front, not an opacity threshold, dilation, color-key cleanup or fabricated fill. Both comparison sides receive the SAME underlap. Final sampled12native oral regions195,315..280,340 have minimumalpha255 and zero below240; this is coverage evidence only, not accepted lip anatomy. All104final upper315head rows are byte-exact between sides. Source boundaries outside this interior region and artistic joins still require review.

## Rendered evidence and limits

outputs/evan-cartoon-contour-jaw contains normal104frame voiced and muted quarter-speed416frame movies at1280x720/48fps, source816..919(17–19.1667s). Both fully decode. Original PCM272000:306667 is verbatim34667samples; normal AAC decode retains34667. Waveform shows the actual recording with one display-only peak scale; active words/phonemes come from the unchanged alignment plan. Timing boundaries remain unverified; all18previous flagged-region visual reviews remain preserved, not reclassified as accurate.

All104native mouth details, native head samples and full comparison frames were inspected against the selected cartoon design sheet. Width spans55.334–86.188px; original inner-lower control spans320.120–348.534px without two-pose clipping. Minimum jaw triangle area2=45.5; no continuous-FV fallback. These are control-transfer checks, not proof of appealing motion or accurate synchronization. No independent listening or continuous-playback acceptance claimed.

Five-Plane-Contour-855.psd contains ACTUAL posed pixel planes (neck, skin underlap, cavity, jaw/lower lip, upper carrier). Reload premultiplied mean error .0233506/255; not native bones or a fully separated mouth. No generated artwork this pass. The reused simplified jaw retains its2.4634px held-out registration residual and placementAccepted=false.

Compared with the lively concept, lips remain too outlined/flat, closed transitions can look like a narrow slash, F/V reads as a toothed grin rather than convincing lower-lip pressure, face/chin/neck paint joins remain angular and brows/eyes lack acting. The contour is less reduced, but this remains below the agreed review milestone. CPU raster can produce meaningful proofs; coordinated component drawing and animator judgment remain the quality constraint. Three contour tests, the new actual-underlap/source-invariance test and nine existing regression tests pass; none imply studio quality.

## Next concrete work

Preserve the continuous contour and skin-underlap tools. Draw/register a truly independent thin lower-lip pressure/roll component, then separate upper incisors and lip paint from the carrier with coordinated F/V-to-vowel release. Use the original full oral controls, voice and uncertainty. Do not return to the two-pose clamp, generate whole heads, threshold-clean seams, broaden staging or promote this experimental exposure. Artist review/redraw is still needed. Main/V3/V4/approved releases/native Moho projects/updater remain protected; no merge, deployment or Moho operation.
