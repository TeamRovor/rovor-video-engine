# Tiny → little: acoustic evidence beside actual continuous lips

`evan-engine/reviews/trace_tiny_little.py` reuses the original PCM reader, centered25ms/5ms spectrogram and actual geometry-capture pipeline. It traces259samples at480Hz across2.28–2.82s, preserving the current plan and both2.36s/2.65s word hypotheses. Four oral meshes at sourceframes56/63/64/67 match actual raster geometry to1e-9. Original speech pixels below310 and v3→v4 pixels below240 remain guarded; geometry controls are authored performance, not measured human anatomy.

Both hypotheses lie inside continuous voiced energy. The largest adjacent spectral cosine change is at2.31746875s, before both proposals, and cannot be treated as a word-edge detector. The current inner lip gap is continuous through2.65s and is12.3107native pixels there. No exact boundary is established; retain the acoustic interval without retiming. All18flags remain unresolved.

Separate local review at workspace root: `outputs/evan-cartoon-tiny-little-trace/Review.html`. It includes30byte-exact full-stage frames from original2–3.25s, complete30/120-frame normal/slow decodes and20000exact PCM samples32000:52000. AAC remains lossy. The two native-resolution plot halves, native faces63/64, four normal decoded samples56/63/64/67 and two slow samples were inspected. The sampled drawing remains coherent but has the same modest acting and limited expression range as the full candidate.

Executed self-checks cover fixed source/plan hashes, centered spectrum times, trace bounds, actual raster/geometry agreement, lower-face preservation, clip frame hashes and exact original PCM. No timing, control, artwork, default or full-film change. Listening, exact phonetics, real-time acting and polished acceptance remain pending. Main, V3/V4, approved symlinks/updater and native Moho projects remain preserved; Moho was not launched or probed.

Next: Region02that’s→not around5.64s versus the older5.17s anchor, using original PCM/spectral evidence and actual oral/tongue controls. Do not infer timing accuracy from energy or mesh coverage.
