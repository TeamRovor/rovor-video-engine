# Evan continuous hand/forearm source and registration study

Two built-in imagegen source plates now supply a continuous thumbs-up hand and bare forearm. This removes the artificial source boundary at the wrist. V1 was generated from the cartoon design sheet (style), existing thumbs-up plate (pose) and actual arm review (color/proportion). V2 is a targeted matte/background edit. Exact prompts and byte-for-byte raw PNGs are saved in `evan-character/cartoon-v1/thumb-forearm-v1/` and `thumb-forearm-v2/`.

Both1024×1536 RGBA plates were inspected at native resolution, with beige alpha composites; V2 is selected for a registration study. Four curled fingers/thumb and continuous wrist skin read clearly in the established cartoon style. V2 is a new plate: outlines/silhouette shift slightly, so old guides are not reused. Neither plate is a registered working rig component.

The raw tool preview suggested brown glow. Proper alpha compositing shows that most colored haze is transparent RGB, not a broad visible shadow. Source alpha audit records core251–254. Beyond8px from the half-alpha silhouette, V1 has1669 alpha1 pixels(totalmass6.5451); V2 has194 alpha1 pixels(totalmass.7608). Nearopaque core/stray pixels remain, with no cleanup, keying, normalization or transparent-RGB deletion. Source PNGs stay unchanged.

## Registration and acting study

V2 measured transverse source guides: y850 center599,width236; y1300 center675.5,width353; y1400 center694.5,width321. These are alpha>=128 measurements, not source modifications. The first maps near actual wrist810,762. The source uses a working component mesh and original navy arm material retains an authored cuff ownership boundary. Generated forearm is underneath retained clothing; no whole-character sprite swap is involved.

First trial bent the entire new forearm through the old material arc. Twelve retained cells reversed(minarea2−14.5680) and the proximal cut was exposed. Rejected; no cells were selectively removed to hide the failure. A rigid forearm parent derived from the actual arc wrist, with continuous independent wrist skin, avoids those reversals. A long proximal tail still protruded beneath the cuff; truncating its component domain toy1350 reduced the protrusion but did not hide the cut. The shortened trial remains REJECTED. Raw source/domain ownership and working geometry must not be confused with an accepted attachment.

Local outputs: `outputs/evan-cartoon-thumb-forearm-source/`. Native Normal48/Slow192 and official Stage-Normal48/Stage-Slow192 films at24fps all fully decode; slow films are muted quarter-speed. Forty-eight wrist samples at held raised elbow retain positive component geometry(minarea2=5.121016203833074). All48native hand/wrist crops and full-stage extremum were inspected, plus three native pilots per construction. The wrist band from the previous separate-hand trial is gone; the forearm/cuff registration and exposed cap now fail. The body/face remain held, digits are a fixed drawing and the gesture has no narration synchronization. This is construction evidence, not polished acting or production approval.

The registration prototype and rejected variants remain frozen locally. No engine code, speaking profile, alignment, default renderer, release, updater or native Moho project changed. Normal/slow review quality is judged visually, separately from positive geometry and decode checks.

## Next concrete work

Derive the actual posed cuff-opening guide from the retained source boundary, then constrain the new forearm's proximal guides/underlap to it while preserving the distal wrist/hand construction. The current rigid plane extends past the curved cuff opening; more tail clipping cannot fix that mismatch. Require positive retained geometry and a hidden cap throughout wrist±15°, then review normal/slow native and branded shots. Do not expose thumbs-up on the low-arm lift or integrate with speech before the attachment passes. No further artwork generation is needed merely to replace this source plate.
