# Drawn lower-lip roll: construction and registration trial

The current contact still reads as a narrow tooth seam. This pass changes the artwork rather than adding another numerical mouth blend. Built-in image generation produced two full-head contact construction studies, followed by one isolated lower-lip/jaw drawing. Exact prompts, input hashes and unchanged generated originals are under `evan-character/cartoon-v1/fv-redraw-v1/source/`. The full heads are unregistered source studies, never replacement head frames. V1 still read as clenched teeth; V2 reduced the visible teeth and made the peach lower-lip cushion clearer, but convincing incisor/lip overlap remains unresolved.

The isolated jaw contains its own painted lower-lip volume, contact fold, chin and jaw skin; no teeth, upper lip, tongue or complete head. Native light/dark alpha composites were inspected. Source alpha is retained; there is no color-key removal or threshold cleanup. The new fold is rather heavy and includes a highlight that may be too glossy for the selected cartoon style.

## Actual registration trial

Naively using the old fixed source canvas placement made the new chin too long and left a doubled cheek outline. That trial is rejected. Three manually annotated source attachments/chin anchors were then fitted to the corresponding anchors on the previous jaw source, followed by the existing native-canvas transform and source-edge correspondence. Matrices/anchors are recorded in `Anchor-Registration-Trial.json`; this does not imply a full contour or anatomical fit.

The lower alpha contour below native y345 was held out of the three-anchor fit. Symmetric outline distance over 558 contour samples is median0, 95th percentile1 and maximum1 native pixel. This confirms a useful silhouette match for a component trial, not anatomy or acting. Native assembled frames851/855/892 were inspected. `Contact-Jaw-Candidate.png` is a REGISTERED CANDIDATE, not an approved runtime component. Existing upper face, mouth cavity, tooth/contact treatment and neck remain separate unchanged planes. No flattened head replacement or face crop is used in the assembly test.

A four-plane posed PSD at851 reassembles with mean premultiplied error0.023247/255. These are actual pixel planes, not blank art templates or native Moho bones. Reassembly is an export check only. The renderer is a bounded scratch study at `work/cartoon-fv-redraw/render.py`; no new default profile, abstraction or asset loader is added to the engine.

Voiced comparison:104normal/416mutedquarter-speed frames,1280x720/48fps, source816–919(17–19.1667s). Original34,667PCM16/16k samples272000:306667 and exactly34,667decodedAAC samples; both films fully decode. AAC is not waveform-identical. The excerpt starts during website and contains feel/finished. The new contact jaw is deliberately applied across all frames for this component test, not a pose-switching rig. All104 upper288rows remain exact between sides; no fallback or inverted jaw triangles. No independent listening or continuous-playback acceptance.

## Review result

The new lower-lip fold adds drawn volume and the anchor fit removes gross jaw drift. It does not fix the old foreground contact plane: the tooth opening still resembles a smiling seam rather than a convincing F/V bite. On release the fold can read as a second crease beneath the mouth. One contact drawing mapped across all vowels is not a coordinated pressure/release rig. Hair, brows, eyes and expression acting are unchanged in this component comparison. The selected cartoon concept still has more appealing and varied expressions.

Do not promote this candidate or its full-head references. Next establish a coordinated upper-lip/incisor contact plane and a matched release jaw drawing in the same native guide; verify actual lip wrap and fold reduction before testing a complete thought. Do not repeat the same full-head prompts or turn isolated seam extraction into rig artwork. Human character-art/animation review remains necessary for pressure, appeal and expression design. CPU rendering is adequate for these proofs; generation consistency and artistic construction remain the limits.

Source timing/phonemes, all18 visually reviewed but unverified acoustic regions, body/staging, official Rovor branding, main/V3/V4/approval updater and native Moho projects are unchanged. Full polished milestone remains incomplete; automation active.
