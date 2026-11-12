# Cheek ownership / neck backing exposure

The review assembly now has three actual planes: newly painted neck backing, a flatter combined jaw/lower-lip source, and the existing upper face with explicit front cheek wings. Removing the old neck from the front carrier avoids carrying an old complete jaw/neck silhouette behind the new jaw. The cheeks now sit in front of the jaw. This reduces the long horizontal mask boundary seen in the previous exposure; it is a layer-order/ownership change, not an opacity wash or new painted cheek artwork.

The two new raster source parts were generated with built-in imagegen, inspected on native-resolution opaque alpha composites, and normalized into fixed native canvases without color keying or opacity extraction. Original source files/alpha remain unchanged. The requested source dimensions and silhouette were not preserved exactly by the generator. Sampled jaw lip/chin edge residuals are -1/+1/+3/+5px against authored guides. In particular the chin shape shifted; no exact likeness/registration claim follows from the top-face preservation check.

## Assembly review

The oversized shiny lip pillow is reduced and the drawn neck is independent of the moving jaw. The result is closer to the clean cartoon direction than the preceding shaded mask test. However, full-resolution consecutive frames still show weak contact drawing, a fine lower-lip gap/stripe, prominent tongue, remaining cheek tonal boundaries and a weak under-jaw cast shadow. The generated jaw changed the chin shape. Three oral/jaw ROI samples (738/741/742) have57/44/41pixels below50%alpha where the preceding test was at least240/255opaque. The ROI includes lip AND chin edges; these counts are a coverage failure diagnostic, not a lip-only anatomical measurement. Do not promote this assembly. Proper sealed lip/cavity overlap and drawn correspondence are still missing.

An early ownership-mask trial lost a band below the glasses: inverse-remapping the finite mesh's coverage left a strip above its moving top row. The final implementation forward-maps the ownership boundary and fills from the canvas top. The final60frames keep the original upper288rows exact; maximum nose-region RGBA change is0. Two regression tests cover upper/nose coverage and complete removal of the old neck from the front carrier. Four existing lip/chin/rounded-crest/fullFV-guard tests also pass. Tests establish these controls and coverage properties, not artistic or studio quality.

## Render and editable-layer evidence

The normal A/B film compares the previous guided jaw/cut carrier with the new three-plane exposure using the same recording and controls. It contains60frames at1280x720/48fps (source714–773,14.875–16.125s), plus a muted quarter-speed film240frames/48fps. Both films fully decode. Narration is the unchanged20,000sample mono16k crop238000:258000; all20,000samples decode from the normal export. Source WAV is exact; AAC is not waveform-identical. All mesh triangles remain positive, minimum doubled area34.112396. The saved prior-frame738/741/742 candidates are byte-exact to the preceding exposure. Native sources, corrected pilot742 and consecutive736–743frames inspected. No independent listening or continuous-playback acceptance.

Posed-Overlap-741.psd contains the THREE actual posed planes, not blank layer names. Reloaded mean premultiplied error is0.020906/255. It is not a native Moho bone rig and does not separate upper lip/lower lip/jaw into independent painted shapes. The original drawing templates remain blank workspaces.

## Next / safeguards

Next design sealed upper/lower lip and cavity overlap in full-face context, using compatible alpha edges rather than filling the measured holes with an opacity or color wash. The front carrier still borrows the existing mouth; proper independent lip drawings and a restrained cast shadow are needed. Human character artist/animator redraw and performance review remain necessary. Full F/V assembly is unsupported and deliberately fails rather than reusing a stale target; this excerpt contains no full F/V contact. Do not expand the scene or retime phonemes to hide the art problem.

Main/V3/V4, approved release symlinks/updater, native Moho projects and default renderers unchanged. No Moho launch. All18flagged regions retain prior visual waveform/spectrogram review and unverified exact phone boundaries; no labels changed. CPU raster rendering is available; missing compatible drawings remain the limiting factor. Full polished milestone incomplete; automation active.

## Files

- [Normal comparison](Overlap-Comparison.mp4)
- [Quarter-speed comparison](Overlap-Quarter-Speed.mp4)
- [Actual posed layers](Posed-Overlap-741.psd)
- [Jaw source](Jaw-Source.png)
- [Neck source](Neck-Source.png)
- [Exact built-in prompts](Prompt-Set.md)

Sources: evan-character/cartoon-v1/jaw-overlap-v1. Review output: ../../outputs/evan-cartoon-jaw-overlap.
