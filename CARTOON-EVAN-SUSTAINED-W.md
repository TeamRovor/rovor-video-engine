# Give W a visible continuous gesture

The development planner now sustains W through its assigned span and gives it full visible-gesture salience, like vowels and lip contacts. Previously W used a capped midpoint consonant pulse at 0.4 salience, allowing a near-idle mouth inside a long assigned W. This is a bounded articulation fix, not an assertion that the aligner's W boundaries are correct.

Reused the existing vowel attack/release envelope. No new profile, smoothing filter, per-word exception, art replacement or timing edit. Energy still modulates jaw opening; the existing independent rounding/chin/corner paths remain in use. Explicit silence gates, P/B/M seals and F/V contacts retain their existing dominance. The fallback pronunciation planner is unchanged.

At 18.225s in `way`, jaw F weight changes from 0.000264596 to 0.775496735; unmodulated identity F is 0.943396226 and its existing smoothed identity is 0.843055673. This removes the control dropout; it does not verify that the recording actually contains W at that exact instant. Low recorded amplitude does not automatically mean silence.

## Correcting the previous experiment

The earlier in-memory experiment replaced `speech_planner.acoustic_weights`, but `rounded_cartoon_head` had already imported the original function directly. Its identity/corner path therefore retained the old function while its jaw path used the candidate. Those renders and geometry measurements describe a **partial-control trial**, not an exact execution of the archived source patch. The silence/energy ablation finding remains valid. The old review is marked historical and corrected; its visual rejection must not be used to conclude that the source artwork alone caused the failure.

Re-ran the envelope-only trial using a patched module imported before every downstream module. Assertions verify that jaw and rounding use the same function. These corrected proofs are in `outputs/evan-cartoon-w-complete-trial`: two normal/slow context comparisons, all 96 native mouth pairs, and 1307 geometry samples. Envelope alone still reads mostly as a thin horizontal smile. Existing pure-F and mixed-F pose renders show that the current artwork can form a small rounded mouth; weak control strength was also preventing that pose from being reached. A redraw was therefore deferred while correcting the controls.

The final sustained-and-salient candidate was rendered through fresh module imports and compared semantically with the final production source using the parsed Python syntax tree. These are actual ten-plane rig renders, not concept plates or newly generated art.

## Rendered evidence and limits

`outputs/evan-cartoon-w-gesture` contains before/after shots for **all four W occurrences** in the recording: `website` twice, `way`, and `we`. Source frame ranges are 24:72, 812:848, 850:898 and 924:960. Each has a voiced normal-speed film and a muted quarter-speed film: 168 normal frames and 672 slow frames in total. All eight films fully decode; source PCM crops and AAC decode lengths are 16000/12000/16000/12000 samples. No end trimming or re-quantization of the source PCM.

All 168 native mouth pairs, selected full native heads, and the selected cartoon design sheet were visually inspected. The revised W reads as a smaller pursed/open gesture rather than the former wide idle line, especially in both `website` contexts and `we`. It anticipates and releases into neighboring vowels. The long `way` still opens/widens toward EY and its exact timing remains unverified. Existing thin closures, abrupt short-vowel/contact releases, limited cheeks/eye acting and finger articulation remain. No independent listening or real-time continuous-playback acceptance was performed.

All 168 upper-face comparisons retain exact upper 288 rows. All 1307 recording-frame/phone-midpoint geometry checks pass; minimum jaw triangle area is 27.78942. No fallback was introduced. Width maximum step remains 13.84723px, but width p95 **increases** 6.23685→6.73285 and 53 individual steps grow by more than 1px as W becomes more visible. LowerY maximum remains 14.66776; p95 is 6.19515→6.10012, with seven steps growing by more than 1px. Chin maximum remains 2.30136. These are control measurements, not proof of smoother perceived motion.

Three new regression tests cover long-W persistence in both jaw/rounding controls, short-W continuity/release, and retained silence/contact dominance. The old planner fails two of them. Existing planner, rounding, duration, separated-face, geometry and scene checks also pass. The final normal-import suite has 49 tests.

This is integrated on the development branch for further animation work. It is **not studio-quality acceptance or a polished milestone**. Main, V3/V4, approved releases/updater and native Moho projects remain untouched; no Moho probe, merge or deployment. The previously rendered full five-second staged scene predates this fix and must be re-rendered before being presented as current.

Next: update that coherent Rovor scene with the new W controls, then address vertical release/short-AO pops against the original recording without erasing complete seals. Independent sound-boundary review and artist/animator judgment are still needed; native 512px source art and the 8GiB CPU renderer limit detail and throughput.
