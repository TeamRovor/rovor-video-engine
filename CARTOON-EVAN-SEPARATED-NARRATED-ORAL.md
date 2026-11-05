# Evan: nine separately rendered oral/face planes on original narration

Historical nine-plane milestone; current ten-plane TH/DH extension is documented in CARTOON-EVAN-DENTAL-SEPARATED-ORAL.md. Its source clips/evidence remain unchanged.

The independent lower lip is now connected to the original continuous narration controls together with separately sampled upper lip, incisors, cavity and tongue. The review upper-face carrier contains clean skin/cheeks and preserved brow output rather than a combined mouth image. This is working component separation on a voiced test, not a polished animation or a full-English production profile.

## Construction and scope

separated_oral_review.py reuses the existing head as the planner/control driver. It records clean face, painted cavity and gated tongue; renders the existing rigid incisor material through the mouth interior; maps the new lower lip with original F/V strength as thickness pressure; maps the existing upper cap along the upper inner arch; and moves the clean jaw through the full lower contour. All source drawings remain unchanged. No whole-head swap, source cleanup, two-pose release normalization, new pronunciation guess or timing adjustment.

Nine planes back-to-front:neck, actual drawn skin underlap, cavity, tongue, rigid incisors, jaw skin, independent lower lip, independent upper cap, upper face/cheeks. Tongue is legitimately inactive at F/V contact; it is actual source material, not an empty artist-template placeholder. Eight/nine-plane authored source studies remain preserved separately.

The original non-oral lower-face blend/native8bit stage and post-oral brow repair are preserved above a protected310px guard. Below it the face uses clean drawn skin, avoiding the old resting-mouth blend. This is still a review construction with authored cap profile and fixed native source geometry; mouth poses crossing the guard reject. Brows remain combined with upper face; this is not a fully separated eye/brow rig.

arch_surface extracts the existing lip UV operation for reuse by the upper cap; source-edge/target ordering, finite coordinates and positive thickness validate. MaxillaryCartoonHead extracts its existing rigid tooth method without changing default teeth_surface branches. No default/profile/config/export/updater changes.

## Defects found and corrected

Initial pure-F/V endpoint comparison failed by165RGB levels: the inherited interior matte used a different material path at exact contact. The new crown now clips through the SAME painted cavity backing at zero/mixed/full F/V. Both endpoint epsilon tests pass at maximum2/255; they also poison stale painted targets to verify fresh geometry. This does not validate contact anatomy.

Initial face reconstruction omitted the original non-oral blend/brow postpass and had one-level upper-face sampling differences. Reproducing those stages corrected the mismatch; final all104upper288head rows are byte-exact and protected nose delta0. The new capture itself is byte-exact to the original head in a focused material-instrumentation test. Initial native pilots are retained with their label and not represented as final frames.

An upstream TH/DH feature composites a dental tongue tip over the incisor edge. That front overlap has not yet been separated into its own plane here. The new review explicitly REJECTS active TH/DH instead of silently baking tongue into the crown or losing that feature. Original production/experimental heads retain their previous behavior. The validated17–19.1667s test contains no dental phones; do not call this complete39-phone coverage.

## Rendered evidence

outputs/evan-cartoon-separated-oral contains104normal voiced and416mutedquarter frames at1280x720/48fps, source816..919. Both fully decode. Original PCM272000:306667 is verbatim34667samples; normal AAC decode retains34667. All104native mouth details, native head samples and full comparison frames were inspected against the selected cartoon sheet. No independent listening or continuous-playback acceptance claimed.

All104native oral regions195,315..280,345 have minimum alpha255; minimum jaw triangle area2=45.5. Width55.334–86.188px and lower control320.120–348.534px use the existing continuous planner. Coverage/valid meshes do not demonstrate convincing animation or precise sync.

Nine-Plane-851.psd and Nine-Plane-855.psd reopen with mean premultiplied errors .025716/.025155 per255. Nine real material layers; tongue is inactive at851 and active at855. Not native Moho bones. Nine focused/regression tests pass:four separation/endpoint/capture/unsupported-dental checks, two lip material/input checks and three existing maxillary checks. No new artwork generated this pass; cap/lower-lip provenance metadata now records the limited voiced consumer while keeping complete-recording/default readiness false. Source hashes are saved in Source-Ownership.json.

## Audio evidence and artistic judgment

Additional review flag reviews/way-separation-review-v1.json records the existing way allocation W330ms/EY100ms. Way-Waveform-Spectrogram.png shows actual PCM and16msFFT/2mshop evidence over17.7–18.5s, with existing boundaries overlaid. A pronounced low-energy interval lies inside assigned W and MAY include a pause; this does not establish an exact phoneme boundary. Word onset, W/vowel transition and existing silence gating require review. Do not delete real pauses or retime merely to keep the mouth busy. The original plan and all18earlier flagged-region visual reviews remain unchanged/unverified.

Compared with the concept, the mouth is still restrained, shallow and too straight across the top; F/V becomes a thin tooth band rather than convincing roll/tuck, and W/rest intervals can look like a held slash. Pressure is still a thickness proxy. Angular jaw/skin/neck joins and limited eye/brow acting remain; the simplified jaw's2.4634px registration limitation persists. Removing baked mouth layers is meaningful engineering progress, not studio quality. Human character-art/animation review/redraw is still needed; CPU rendering can already produce proofs.

## Next

Separate the existing TH/DH front tip overlap before extending this construction to the complete recording. Review way onset/pause allocation and silence gating against the audio; keep timing unchanged until supported. Then improve designed lip roll/tuck and rounded shapes using these independent components before restoring the broader body/staging shot. Preserve main/V3/V4, approved releases/symlinks/updater and native Moho. No Moho operation, merge or deployment. Full polished milestone remains NOT ready; automation stays active.
