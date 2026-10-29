# Registered neck and collar artwork

The previous neck experiment exposed pale slivers and a larger left-side gap at -8 degrees. This optional component replaces the fragmented collar opening with locally registered redrawn collar art, and supplies a broad continuous hidden neck behind it. The neck mesh widens progressively below the jaw to match the original shirt opening; its base stays fixed while the upper end follows the head. Original facial acting remains pixel-identical to the previous neck study at the inspected narration extremes. No new generated face is used.

## Sources and working components

Built-in imagegen produced two transparent construction plates: `neck-source/extended-neck-v1.png` and `neck-source/collar-empty-v1.png`. Exact prompts and the visible collar input are stored alongside them. These plates are source art, not registered rig parts. `build_cartoon_neck_art.py` registers them into `neck-art-rig/neck.png` and `torso.png`. Stable-feature ECC values 0.99289 and 0.99791 describe registration only, not visual confidence. The torso edit is bounded to x430–590/y280–400; all other torso pixels stay exact. The upper neck retains the animated original jaw ink/shadow, with generated art supplying the hidden lower overlap.

Select `CartoonNeckArtBody` or `render_cartoon_gesture_study.py --neck-art`. Older classes and defaults remain comparison baselines. `export_cartoon_body_psd.py --neck-art --time 2.4` exports seven independent pixel layers; the reopened PSD mean premultiplied difference is 0.0074/255. This is a local raster mesh rig, not a verified native Moho bone project.

## Render review and limits

The 4.8125-second, 48 fps narration study reuses the actual script/audio plan and official Rovor mark. A muted 19.25-second quarter-speed version accompanies it. Native before/after views use identical t=2.4 controls with body roll zero and head tilts 0/+8/-8. Additional native checks cover the narration's minimum/maximum jaw displacement (0 and 6.58 source pixels) and a separately labeled synthetic full-D jaw target (22 pixels). In these inspected views, the pale neck/collar gaps are closed and old rim speckles are removed. The new collar is continuous; the source plates have become separate moving neck and fixed torso components rather than a full-character sprite swap.

There is still a small angular dark fold below the left jaw, most apparent in the -8/full-open stress pose. The overlap is limited to in-plane tilt; no head turn or convincing 3D neck anatomy is claimed. No continuous movie playback/listening verification is claimed: review used full-resolution component, native extreme and sampled rendered frames. The normal/slow films remain available for perceptual review. 95 checks pass for construction, attachment, local edit protection and previous behavior; they do not establish animation quality.

This change does not improve or retime the mouth performance. The final rendered frame at 4.7917 s (logo) exposes a muddy brown neutral-to-UW lip transition: X=.5405 / F=.4595, with no F/V contribution. That is a concrete oral-surface blending defect to fix, not evidence of an alignment correction. F/V lower-lip anatomy, L/tongue shape, pointing-hand linework/wrist contour, shoulder creases and broader acting still need work. Legs remain static, and there is no eye/blink rig behind the glasses. All 18 timing disagreements already have waveform/spectrogram visual evidence review; exact phone boundaries remain unverified. A character artist/animator remains needed for final anatomy, transitions and performance. CPU rendering limits iteration speed; more hardware cannot replace missing drawings.

## Next bounded work

First isolate and fix that neutral-to-UW oral blend using native intermediate frames around logo, keeping the recording timings fixed. Then use this cleaner assembly in a longer narration scene through favicon and its real pause. Design an actual relaxed-to-point hand transition, with anticipation and a held gesture on the relevant words; the current pointing drawing is held throughout. Review it at normal speed before adding more secondary motion. Preserve the existing timing uncertainty and ask no routine decisions.

Main, V3/V4, approved release/updater and native Moho files remain untouched. The full polished cartoon milestone remains incomplete, so the development automation stays active.
