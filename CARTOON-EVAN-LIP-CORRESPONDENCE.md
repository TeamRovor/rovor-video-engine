# Source-matched lip edge and painted mouth-cavity backing

This pass changes rig correspondence and material ownership, not source artwork or speech timing. It registers the lip-bearing edge of the existing jaw drawing to its actual fractional alpha contour, rather than assuming that the generated drawing exactly follows its guide. It also places the existing painted mouth cavity behind the lip joint as a separate material plane. The previous front carrier contained the mouth image but did not supply cavity depth behind the adjoining jaw edge.

## What changed

`lip_surface_correspondence.py` measures the existing source edge near explicit guide knots and builds a non-inverting source-coordinate mesh. The threshold locates a contour for rig registration ONLY: it never cleans, binarizes, fills or repaints source alpha/RGB. Target mouth geometry, phone/word times, jaw/chin controls and the original source files are unchanged. Correction is restricted to the lip-bearing band and fades out above the chin. Chin drift in the generated drawing is deliberately NOT fixed by this pass.

`corresponding_lip_exposure.py` captures the already-painted cavity from the existing renderer and places it behind the registered jaw/upper-face joint. This is an actual cavity material with existing artwork and geometry, not skin-colored gap paint or an opacity wash. Four posed planes are now visible in the review PSD: neck, cavity, combined jaw/lower lip, and the existing upper face with cheek wings. Upper lip/face still borrows existing mouth art; lip and jaw are not yet independently drawn shapes. Full F/V is still explicitly unsupported.

## Full-resolution comparison

At planned contact frame738, the previous oral ROI had120pixels below240/255alpha. Source-edge correspondence alone leaves51; cavity backing alone leaves75; both leave0. Release741 is115/50/30/0. Frame742 is106/52/0/0. The native four-way comparisons distinguish the two changes instead of treating a passing test as visual approval.

Across all60frames in fixed oral ROI[190,318,280,365], below240alpha frame-pixel events fall from8,589 to56; no pixels remain below128. The residual56events occur in10frames, with alpha225–239. They are faint edge translucency, not a perfectly opaque surface. Each residual frame was re-examined and locations logged in Residual-Coverage-Diagnosis.json. Do not call this a complete contact/anatomy correction from an alpha count.

Native head frames738/741/742, consecutive736–743 and the native ablation heads were inspected. The obvious pale lower-lip strip is removed in the reviewed contact/release samples. The remaining mouth is still plain: bilabial pressure/roll is not designed, tongue prominence and tooth-strip styling persist, the chin shape and cast shadow need artist work, and expressive face/eyes are unfinished. Source registration and backing improve a visible defect; they do not establish studio quality, correct phoneme boundaries or natural performance.

## Verification and files

Normal comparison60frames at1280x720/48fps; muted quarter speed240frames/48fps. Source714–773 (14.875–16.125s), original mono16k narration samples238000:258000. All20,000samples decode from the normal movie; AAC is not waveform-identical. Both movies fully decode. Target triangles stay positive, minimum doubled area34.112396; calibrated source triangles minimum45.5. Upper288rows and everything below row400 remain byte-exact to the preceding exposure for all60frames. Three saved before-samples reproduce the prior c1550aa images exactly. Tests also protect the nose in the contact sample. No independent listening or continuous-playback acceptance.

Three meaningful regression tests pass with the local recorded plan (ROVOR_REFERENCE_PLAN can override its path; the two recording-dependent tests skip if it is absent, while the source-preservation test still runs): read-only source/chin-band preservation; material coverage in the planned contact sample without identity/neck changes; coverage and four actual planes in release samples. Posed-Mouth-741.psd reloads with mean premultiplied error0.021405/255. This is posed raster-layer reassembly only, not native Moho bones or an approved facial rig.

No image generation this pass. Existing jaw/cavity paint remains untouched, with source hashes recorded. Main/V3/V4, release symlinks/updater, default profiles and native Moho projects unchanged; Moho was not launched. No timing edits; all18flagged regions retain earlier waveform/spectrogram visual review and unverified exact phone boundaries. CPU rendering is available; artist-drawn pressure/expression shapes and animator review are still needed. Full polished milestone incomplete; automation active.

## Next

Before longer narration, evaluate mixed and full F/V with freshly captured current oral geometry and explicit contact material; never reuse a stale painted target or silently substitute a fallback. Keep this contact/release coverage comparison as a regression reference. Continue independent lip/contact artwork and source-shadow design; do not use coverage metrics to approve performance or retime speech to hide missing drawings.

- [Normal comparison](Corresponding-Lip-Comparison.mp4)
- [Quarter-speed comparison](Corresponding-Lip-Quarter-Speed.mp4)
- [Actual four posed layers](Posed-Mouth-741.psd)
- [Native contact ablation](Ablation-738-Review.png)
- [Consecutive frame review](Transition-Frame-Review.png)

Sources: unchanged jaw-overlap-v1/Jaw.png and painted-oral-parts-v1/Cavity.png; registration in lip-correspondence-v1. Review files: ../../outputs/evan-cartoon-lip-correspondence.
