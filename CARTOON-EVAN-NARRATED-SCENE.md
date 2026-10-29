# Narrated scene with an articulated index

The earlier scene held a pointing drawing throughout the narration. This optional 10.1875-second study now anticipates the globe/up here phrase, holds a point toward the tab, returns toward a soft curl, points again on favicon, and settles the arm/index during the real following pause. It combines the current layered cartoon head, separate phone-driven lip width/audio-driven jaw, authored brows, registered neck/collar and independent arm/wrist chains.

## Real components and controls

Built-in imagegen produced `index-source/hidden-palm-v1.png`, removing the extended index while retaining the palm/thumb/three curled fingers. The exact prompt is stored beside it and copied to the output folder. This is a construction source, not a complete hand or registered rig part. `build_cartoon_index.py` registers the hidden palm to the original pointing source using the forearm/wrist reference (ECC 0.97343; a registration diagnostic, not visual confidence). Only a versioned hand component changes; the character, torso and approved assets are preserved.

The first local socket patch cut through thumb/finger outlines and left a visible notch. Final construction instead uses the coherent registered hidden palm below a feathered wrist transition, keeping the original proximal forearm. The extended index is extracted from the original point drawing as its own surface. Three hierarchical phalange transforms and broad skin weights bend that surface continuously. No finger drawing crossfade or whole-character sprite replacement. Initial sharp weights pinched/folded the mesh; the final inspected angle range is MCP -10..0, PIP 0..60, DIP 0..35 degrees, with broad bend transitions and a guard against unreviewed ranges.

Only the index is articulated. The thumb and other three curled fingers remain one palm drawing; this is not an independently rigged five-finger hand. The rest pose is a loose index curl, not a newly drawn fully relaxed open hand. Bending the straight artwork cannot create artist-designed folded creases or volume. Thin hand ink and the wrist/forearm contour still need cleanup.

`CartoonSceneBody` / `render_cartoon_scene.py` is a new opt-in scene. `scene_events` anchors two authored gesture phrases to the existing word times; `scene_controls` adds a small drawback, delayed elbow/wrist/finger follow-through, stable holds and a pause settle. These are authored acting choices, not automatic emotion inference. The browser remains a default globe, highlighted when the narration names favicon; the scene does not falsely demonstrate a website update. It uses the official Rovor mark. Previous renderers and labels remain defaults; the new scene omits engineering captions.

## Review artifacts

Normal film: 489 frames at 48 fps, source 0–10.1875 s. Muted quarter-speed: 1,956 frames/40.75 s. Both final files decode fully with no reported errors; see Review-Timing.json. The source recording and existing word/phone annotations are unchanged. The clip reaches almost the end of the annotated 9.15–10.19 s pause, before the next spoken phrase. During its central 9.35–10.02 s region, the existing mouth planner is fully at rest; no new silence timing is claimed.

`Evan-Scene-Layers.psd` reopens with eight actual pixel layers: neck, torso, left hand, left forearm, right index, right palm, right forearm and head. Mean premultiplied pixel difference from runtime is 0.00747/255. This is an independent local raster rig, not a verified native Moho bone project. Generated source, exact prompt, native curled/half/point composites, scene cue timeline and pause evidence are saved separately from working components.

Full-resolution source/composite and assembled gesture/pause frames were inspected. The extended point reads toward the tab, and the index remains attached in the inspected bends. Remaining weaknesses are obvious in the native hand: hook-like resting index, fixed curled neighbors, limited creases, thin ink and wrist join. The narrow lip at 8.79 s also reads as a muddy gray/brown patch at scene scale and needs local contour/compositing review. Lip contours remain wedge-like/jagged; F/V/L anatomy, shoulder creases, static legs and missing eye/blink acting also remain. No continuous movie playback/listening verification is claimed. Normal/slow films are provided for perceptual review; do not infer professional/studio quality from the geometry checks or export match.

114 automated checks pass. New checks cover all scene frames for index orientation and arm foldovers, shared phalange joints, held anchor poses/pause recovery, safe idle and rejected unreviewed curl ranges. Timing coverage is not accuracy: all 18 existing word-anchor flags already have waveform/spectrogram visual evidence review, with exact phone boundaries still unverified. This pass does not retime the recording or resolve those flags.

## Next work and limits

Build a designed softer hand pose for the remaining fingers and clean the index root/knuckle/wrist drawings, then review the entire scene at normal speed for acting rhythm. Improve rounded/FV/L mouth construction and shoulder skinning with artist-authored/redrawn assets. A human character artist/animator is still needed for anatomical and performance approval. CPU rendering limits iteration speed; hardware cannot supply missing drawings.

Main, V3/V4, approved symlinks/updater and native Moho files remain untouched. No merge, deployment or unattended Moho operation. This is a larger construction/performance study, not the agreed polished final milestone. Automation remains active.
