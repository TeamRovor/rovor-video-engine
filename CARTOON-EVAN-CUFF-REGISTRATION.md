# Evan registered cuff and forearm construction

`CuffRegisteredForearm` binds the existing continuous thumbs-up/forearm V2 source to the actual right-arm wrist and cuff. `thumb-forearm-v2/Cuff-Registration.json` records the source hash, measured source guides, exact target geometry, clothing ownership boundary and underlap. This is an opt-in registered working review component, distinct from the raw source plate. The default speaking scene does not import it.

The cuff-opening guide uses original source points[798,638] and[724,677], posed through the actual arm. A cubic Hermite centerline joins the moving wrist cross-section to the cuff-opening frame. Its proximal guide is20native pixels inside the cuff; another source segment continues beneath clothing. Cross-sections follow the curve normal, while distal hand geometry retains the existing rigid hand parent and continuous wrist skin. The fully proximal frame stays exactly fixed during wrist changes. The original navy material overlays the forearm through an explicit working ownership mask. Raw PNGs and alpha are unchanged.

This fixes the exposed cap seen when the new forearm was a rigid plane. An earlier direct linear blend toward the guide reversed five cells(minarea2−22.1700); rejected. A shorter guide and5px underlap left a background strip. Extending to the actual lower cuff-opening endpoint and using20px hidden underlap closes that strip in the reviewed held raised pose. No negative cells were ignored, source fringes keyed out or broad dissolves used.

## Verification and visual review

Fifteen focused tests pass: four new component tests plus the previous six arc/five hand-plane tests. The new component samples1224shoulder/elbow/wrist combinations within shoulder−5..0°,elbow−135..0°,wrist±15°. All retained triangles stay positive(minimum about2.8381 in the geometry probe); distal material matches the rigid hand parent. Exact proximal hold, invalid poses/wrong geometry and source preservation are checked. Four fresh final-module native frames are pixel-exact to the review sequence after endpoint-roundoff stabilization.

At held shoulder−5°/elbow−135°,14half-alpha source cap samples at each wrist−15/0/+15 fall beneath clothing alpha>=253. This is a sampled underlap check, not a claim of perfect silhouette coverage at every possible pose. Independent fingers and production-quality source matte are still absent.

Local outputs: `outputs/evan-cartoon-cuff-guide/`. Native Normal48/Slow192 and official Stage-Normal48/Stage-Slow192 at24fps fully decode; slow films are muted quarter-speed. The wrist moves0/+15/−15/0 on a held raised arm. Minimum component area2 in that48frame sequence is2.8405059644765887. All48native hand crops AND48native cuff crops were inspected, with three native pilots and full-stage extremum. The cap/background strip is hidden through these wrist samples; the thumb reads cleanly. The old cuff's pointed inner notch/dense shading, nearopaque source alpha, held body/face and fixed finger drawing remain below the requested polished acting. No narration synchronization or production acceptance is claimed.

No generated artwork, speech retiming, release/updater or native Moho operation occurred in this follow-up. The source plate's SHA remainsf2063f694cd5a25e3dbbcb12edbdc2e9778c180e04a033dac46594873ee356b3. Frozen scripts, rejected variants and decoded-film hashes remain local.

## Next concrete work

Build one branded closing-shot comparison combining this registered raised-hand component with the existing separated postroll smile/brow trials. Preserve the speaking context and exact original audio. Use a deliberate shot cut for the new raised pose after actual recording end+.08s; do not switch hand drawings visibly or expose low-arm thumbs-down. Review normal/slow full-stage acting before further detail work. Keep source/face guards and default speaking paths unchanged until that comparison is reviewed. This component is progress toward the milestone, not the completed polished milestone.
