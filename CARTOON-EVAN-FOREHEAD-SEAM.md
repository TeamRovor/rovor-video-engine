# Local forehead skin transition

The broad rectangular skin band comes from two existing construction boundaries: the original brow removal and the upper edge of the later eye-underlay repair. The original browless head, v3 underlay and ownership masks were compared at native resolution before changing pixels.

`build_cartoon_forehead.py` reuses the existing glasses-free source plate, saved affine registration and RGB offset. A traced local skin mask with a three-pixel feather replaces 4847 native skin pixels. It creates separate eye-underlay-v4 derivatives; original source bytes/alpha and v3 art remain preserved. This is registered local construction, not a newly generated head. Outside ownership, all underlay alpha, everything below native y240 and original glasses bytes remain exact. Four derivative files rebuild byte-exact.

`CartoonUpperFace` accepts a keyword-only construction folder; its default stays v3. One added regression checks open/half/closed blink with glasses0/12/25 and independent brow controls, preserving all rendered pixels outside local ownership and below240. Twelve upper-face/eyelid tests pass. The check guards source alpha and every unowned rendered pixel; pixels inside new skin ownership deliberately come from the opaque underlay. Actual stage baselines remain byte-exact.

Separate local review: `outputs/evan-cartoon-forehead-seam/Review.html` at the workspace root. All24 actual poses first reproduce the completed v3 full candidate before the local head change. Oral/jaw audit, native lower face, neck, all other body layers and official stage remain exact. Complete24/96-frame normal/slow decodes and exact16000-sample PCM context cover original6.25–7.25s; AAC remains lossy.

Native before/after underlay and open/closed speech faces were inspected, followed by five normal and three slow decoded1280×720 stills. The broad forehead band is reduced. Small inner-brow flecks, lid/temple/frame edges and limited gaze/expression remain below the concept direction. No real-time performance, listening, phonetic or polished acceptance. All18 timing flags remain unresolved. No full-film/default promotion, Moho operation, merge or deployment.

Next: actual rest/open-eye speech fixtures0/269 and broader glasses raise/return checks, then consider full-shot integration using the same foundation. Preserve the completed v3 full candidate and protected closing.
