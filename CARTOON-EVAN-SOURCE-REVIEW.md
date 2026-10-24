# Cartoon source-art milestone

The latest user direction is an entertaining expressive 2D cartoon, using the photograph as loose identity reference. The new setup drawing and speech poses retain the chosen cartoon hair, sunglasses, navy shirt and tie, with flatter cel shading, simpler folds and a quieter rig setup pose.

New source art:
- setup-v1.png: 1024x1536 transparent full-body setup, level shoulders/head, open hands clear of torso. The alpha-128 silhouette is [130,17,892,1507], and no opaque subject pixel meets the image border.
- speech-poses-v1.png: first complete nine-head source sheet. F/V read as a grin and L tongue lay too low; retain as the rejected first iteration.
- speech-poses-v2.png: targeted refinement improves F/V lower-lip contact and raises the tongue for L while preserving the remaining sheet. These contact poses still require review at actual animation size and in motion.

Source audit uses connected components instead of equal-width grid cuts: the actual hair silhouettes cross nominal third-column boundaries, so naive sheet slicing would clip them. It locates nine separate heads and records real bounding boxes. It also records setup alpha/frame bounds. It explicitly reports animationReady=false; an atlas is not a rig. Run audit_cartoon_sources.py with setup, output JSON and --atlas.

All outputs were inspected at source resolution. Clear cartoon outlines and mouth shapes are a useful step away from the previous realistic painted art. However, small silhouette/angle differences remain across heads, body/head layering is not built, and hidden shoulder surfaces are not drawn. No new animation film is claimed from this source-art pass. Do not substitute full-head swaps for a registered stable upper face and controlled jaw/lips. The first meaningful motion test must evaluate those deformations, F/V/L contacts, and the acoustic P interval in “open” at normal and slow speed.

Next: register heads to a single upper face; mark outer/inner lip, cheek and jaw landmarks; preserve the drawn mouth shapes. Build head/neck and body/arm plates with real hidden surfaces, then export editable layers. Wire the existing acoustic controls into those cartoon components and render an opening-line test. A human animator/redrawn contact shapes may still be needed if generated F/V and L do not read clearly in motion.

Main, V3/V4, approved symlinks/updater and native Moho remain untouched. No Moho launch or probe was attempted. Generated source and exact prompts are versioned beside the concept sheet. The recurring instruction has been corrected to prioritize this cartoon direction and acoustic speech work.
