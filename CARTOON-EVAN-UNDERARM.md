# Local underarm artwork cleanup

The new optional CartoonSocketBody uses generated/registered artwork only in two small underarm bands of the existing torso. It retains the separate arm/hand controls and acoustic-driven cartoon head. The earlier CartoonBody and CartoonGestureBody remain comparison baselines; approved/default render routes are unchanged.

## Registration and original-art protection

Built-in imagegen edited a visible, flattened preview of the original armless torso. The raw v2 candidate again moved the shirt vertically and changed its scale. It is NOT used as a whole-body replacement. Center-shirt affine registration, initialized from collar/waist positions, produces an ECC score of 0.97885. That is an image-correlation diagnostic, not a quality/confidence percentage. The registered candidate supplies only masked underarm bands, with a small measured navy color offset. Source, visible input preview, exact prompt, matrix, patch mask, source hash and limitations are saved in socket-source/socket-rig.

build_cartoon_sockets.py blends premultiplied color and alpha within those bands. Pixels outside the mask remain byte-for-byte original, including the entire center strip x430–593, neck, tie and lower body. The derived torso changes 26,925 pixels in total, including transparent color data. The generated whole-body anatomy is not substituted for original art. animationReady remains false.

Native assembled comparison reduces the old dangling black armpit tabs, especially beneath the raised pointing arm. A dark sleeve/torso crease is still visible, and the new band has a slightly different cel-shading transition. This is local cleanup, not a complete hidden shoulder construction or a new range of accepted motion. The neck/collar transition was inspected but remains unchanged and unfinished. No claim is made that a still improvement establishes better acting.

## Preview correction

Some masked source files retain original RGB beneath zero alpha. Inspecting those RGB channels without compositing can misleadingly reveal removed parts of the original figure. Earlier raw transparent PSD-preview views also exaggerated edge speckles. Actual composites on white and gray were inspected this time; the rendered character is cleaner than those raw previews suggested. The exporter now creates an explicit gray-background JPEG alongside the transparent PNG. Future generation/edit references should use a visible composite when inspecting a masked source, while preserving the original alpha assets for the rig.

## Review and validation

Use render_cartoon_gesture_study.py --sockets for the new torso, or omit it for the original pointing study. export_cartoon_body_psd.py --sockets --time 3.2 writes six real torso/head/forearm/hand pixel layers, not native Moho bones. The saved PSD is reopened and compared with assembly (mean premultiplied difference about 0.00561/255). Local outputs/evan-cartoon-joins contains the normal 4.8125-second 48fps narration film, muted quarter-speed film, native before/after and editable sources. The same narration, gesture tracks, face art and Rovor branding are retained to make comparison meaningful.

81 checks pass, including original-art protection outside the masks and preservation of the baseline torso. Existing geometry/speech checks still pass. Source, registered component and white/gray assembled native views were inspected; no production-quality inference follows from passing tests or pixel counts.

Next: a genuinely clean neck/collar attachment, remaining shoulder skinning/crease cleanup, consistent hand linework and a designed pose transition. F/V, tongue and upper-face acting still need artist/animator review. The 18 timing flags remain visually reviewed with exact phones unverified. The local CPU raster renderer limits iteration speed, but missing construction drawings and acting are the main quality limits. Preserve main/V3/V4, approved releases/updater and native Moho; no launch/probe, merge or deployment was performed.
