# Fixed drawing templates and isolated artwork import

Three native 512x512 PSD templates now provide Contact, Release and Open construction workspaces. Nine paint planes separate neck behind jaw, jaw skin, left/right cheek overlap, cavity, upper teeth, tongue, lower lip and upper lip. All paint planes are deliberately blank. These files are an artist workspace, not new artwork or a working facial rig.

Each PSD has a hidden current experimental head reference, a hidden proposed registration guide and nine individually hidden work-envelope guides. Reference and guide pixels reload exactly from PSD; all 27 paint planes reload empty. Toggle references/guides when drawing. Source snapshots 738/741/554 are discontinuous and are NOT a timing sequence. Current rendered mouths are flawed references, not target art. The selected cartoon design sheet remains the style reference.

## Drawing contract

Keep native canvas size and separate ART__ plane names. Paint actual skin/lip volumes with their own alpha, normal blending and full layer opacity. Bake masks/effects into each plane's intended alpha before staging. Never place an entire head or reference plate on a lip/jaw plane. The broad work envelopes are contamination checks, not anatomical accuracy measures.

The proposed mouth corners stay at (194,325)/(263,325) across the three guide poses. Upper lip rises only slightly, lower lip releases downward; chin targets are 393/394/398. These are authored cartoon proposals, not measured anatomy or approved performance. Change the contract deliberately when an artist designs a better construction; do not warp an incompatible drawing until it appears to pass.

Draw compression pressure and lower-lip roll as related cheek/lip/chin volumes. Upper/lower lips need compatible corners and contact sealing. Jaw skin needs an open upper boundary and skin overlap, with no complete mouth painted inside it; neck stays separate behind the jaw. Contact can omit cavity paint; teeth/tongue are optional in these workspaces rather than forced visible strips/blobs. Hidden overlap still needs to be drawn for articulation.

## Import boundary

`audit_face_art_psd.py` reads only recognized ART__ raster planes. It ignores all REFERENCE__/GUIDE__ layers even when visible. It rejects missing/blank required paint, duplicate/unknown layers, whole-head alpha outside plane envelopes, non-native canvas, offset paint outside canvas, masks/effects/clipping and layer opacity/blend dependencies. Valid planes can export lossless PNGs to a new staging directory outside the repository. It refuses existing file overwrites and does not write engine assets or change a runtime profile.

A structural pass ALWAYS reports animationReady=false and runtimeLoaded=false. It does not certify artistic quality, alpha topology, shared contour correspondence, contact sealing, occlusion, hidden overlaps, phoneme accuracy or continuous motion. Those require a separate assembly and voiced normal/slow review before any runtime integration.

## Evidence and limits

Three importer regression tests pass: blank required art fails without partial export; flattened-head art and dependent opacity fail; recognized separated paint exports pixel-exact while visible references/guides stay excluded. All three actual blank PSDs were reopened and rejected as intended. Native guide overview inspected. No new image generation, runtime profile, speech movie or timing changes this pass. No independent listening/playback approval. Prior Maxillary normal/quarter-speed films remain the experimental baseline. No Moho launch; main/V3/V4/updater untouched.

Human character artist/animator redraw and review are still needed for convincing lip compression, jaw anatomy and performance. Available CPU rendering can test an assembly; it cannot supply missing drawings. Full polished milestone remains incomplete; automation remains active.

Next: use the fixed guides to produce one coordinated lower-lip/jaw construction with designed overlap, keeping upper-lip/cheek/neck interfaces explicit. Stage and inspect that source before integrating or rendering it. Do not repeat unconstrained full-head generation, isolated seam glyphs or scalar placement loops.
