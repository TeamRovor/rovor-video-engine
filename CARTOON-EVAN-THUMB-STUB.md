# Evan cartoon wrist-stub registration review

`ElbowArcReview.posed_points(points, angles)` now poses registered component guides in the same source material coordinates as the arm. The arm's own vertices use that shared method, so a hand's wrist stub can follow the actual continuous wrist skin rather than a rigid hand parent throughout its underlap. Finite N-by-2 points and the existing pose envelope are validated. Current speaking scenes remain unchanged.

Eleven focused tests pass: six arc tests and five existing hand-plane tests. New checks cover proximal component guides that must remain fixed during wrist rotation, the moved wrist pivot, distal guides that must match the rigid hand parent and invalid component coordinates. Earlier 1,224-pose structural/parent checks remain included.

## Measured registration trial

Source wrist guides measured at alpha>=128 (measurement only): y1050 edges583/873,center728,width290; y1160 edges578/874,center726,width296. An initial assumed second guide(center733.5,width311) was wrong and is rejected/frozen. The source PNG and its alpha were not changed.

Corresponding existing-arm guides: axial0/−36 relative to wrist810,762 along normalized61,137; transverse center−5.5/−6.75 and width52/47. The upper hand drawing uses a uniform similarity mapping; only the wrist stub changes width/center/axial scale between guides. The component then follows the shared arm/wrist deformation. This is an isolated component mesh, not a whole-character sprite or finger rig.

The full rectangular stub domain produced a negative retained triangle(minarea2−7.67883), and its exposed lower cut was visible. It is rejected. A bounded component ends at sourcey1075(about8px proximal underlap); the retained old arm ends at axial−4. These explicit runtime component domains overlap behind the retained forearm. No inverted cells were selectively discarded and no structural guard was weakened. Raw source files/alpha remain intact; working component ownership changes which material is rendered.

The corrected bounded trial has positive retained hand triangles throughout48frames(minarea2=.9094531223183159). This does not establish visual acceptance. Local outputs at `outputs/evan-cartoon-thumb-stub/`: native Normal48/Slow192 and official Stage-Normal48/Stage-Slow192 frames,24fps, with muted quarter-speed variants. All four films fully decode. The elbow is held raised and the wrist moves0/+15/−15/0. There is no narration synchronization. Frozen scripts, measured guides and rejected variants retain the construction history.

All48native hand/wrist crops plus full-stage extremum were inspected. The thumb pose reads clearly, and the long dangling stub is reduced, but a pale diagonal band and small contour step remain at the wrist join. Cuff notching, dense source contours, held face/body and fixed digits remain below the cartoon direction. The attachment is REJECTED. Neither a production hand component nor polished acting is claimed. The prototype remains local/frozen; only the shared material-point method and its checks are added to the engine.

## Next concrete work

Generate a continuous thumbs-up hand plus bare forearm construction source in the established cartoon style, using the existing hand and actual arm as references. Register elbow/wrist guides and place the proximal source join beneath the rolled cuff. Continue to articulate wrist/hand independently through mesh weights; a continuous skin drawing need not impose a visible wrist seam. Keep the raw generated plate separate from its working component and inspect at native resolution. Do not keep nudging this rejected wrist cut or hide it with a broad dissolve. Preserve the current default scene and all native Moho projects.
