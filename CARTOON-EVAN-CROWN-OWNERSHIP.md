# Contact-incisor ownership diagnosis

The existing F/V source already has separate lip-contact and upper-teeth artwork in fv-rig-v3. The current four-plane jaw study composites those materials into its upper-face carrier before cutting that carrier against the lower jaw. This pass measures what that cut removes; it does not generate another mouth or change a default profile.

`contact_crown_audit.py` captures the actual contact incisor plane after the existing rigid-placement/window treatment, before the upper-face ownership mask. Three tests pass: fractional alpha accounting, source-material partition, and byte-identical mixed/full contact renders with instrumentation. The audit's standalone rendering remains unchanged. Source images/alpha and phoneme timings are unchanged.

Across 19 active contact samples in source848–898, the carrier removes0–48.455% of the incisor plane's fractional alpha area. At851(17.7292s), before/after area is105.960/54.617 native pixel equivalents; opaque pixels103/54. At892 removal is42.906%; at855 it is0. This is ONE mask's effect on ONE material, not final visible tooth area and not proof of a bug. Some crown occlusion by the lower lip is anatomically necessary. FV blending and other foreground paint are separate effects.

## Counterfactual rendered test

`render_crown_ownership.py` keeps the existing fitted fv-redraw-v1 jaw and four-plane assembly, then exposes only the removed portion of the actual crown in front, weighted by the existing F/V amount. No skin fill, alpha cleanup, tooth repaint or new speech timing. This is an ablation: placing the missing crown in front can violate lower-lip occlusion and must not be promoted as an anatomical correction.

Outputs under outputs/evan-cartoon-upper-contact include48normal/192mutedquarter frames1280x720/48fps, source840–887(17.5–18.5s), covering “feel” and “way.” Original monoPCM16/16k samples280000:296000:16,000 original and exactly16,000decodedAAC samples. Both films fully decode; AAC is not waveform-identical. Ten frames have active F/V; all38zero-F/V rendered head pairs are exact. Native baseline851 matches the prior registered-jaw film byte for byte. Upper288rows stay exact. Native851/855/856 and consecutive848–857 inspected. No independent listening or continuous-playback acceptance.

The crown becomes less of a hairline when exposed, but the mouth still lacks designed incisor/lower-lip pressure and appealing contact/release shapes. Restoring all material is not necessarily correct. This finding narrows the construction problem: contact crown placement, upper-face ownership and lower-lip occlusion need to be authored together. It does not justify more isolated seam generation or a blanket “show all teeth” mask change.

Next: establish a native contact construction with explicit upper-lip edge, incisor tips and rolled lower-lip edge, plus a matching release. Compare correct front/back ordering before drawing another source. Existing source art is available; its placement and anatomy need artist/animator review. No full-thought integration or release promotion. Main/V3/V4/approval updater/native Moho projects unchanged; polished milestone incomplete.
