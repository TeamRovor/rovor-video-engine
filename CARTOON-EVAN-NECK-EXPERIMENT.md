# Neck attachment experiment — not accepted artwork

The previous body assembly overlays two neck fragments with mismatched widths and an old vertical chin/neck contour. This opt-in experiment separates the animated head from one deforming neck surface, anchors its base beneath the original V collar and corrects the head placement 12 native pixels to the left. The upper neck follows jaw opening and head rotation; the base remains fixed to the torso. It reuses the selected cartoon artwork. No image generation or native Moho operation was used.

`CartoonNeckBody` / `render_cartoon_gesture_study.py --neck` select the experiment. Existing routes retain the old assembly. The shared head-layer extraction preserves baseline pixels exactly at 0.34 and 2.4 seconds. `export_cartoon_body_psd.py --neck --time 2.4` exports seven real pixel layers (neck, torso, two hands, two forearms, head); it is not a native bone rig. Reopened PSD mean premultiplied pixel difference is 0.0051/255.

92 automated checks pass, including fixed-base/upper-follow behavior, mesh orientation across jaw/tilt sweeps, and preservation of navy collar/remote torso pixels. These checks do not establish visual acceptance.

## Visible review

Native solid-background comparison shows the reduced doubled neck contour and the remaining defect: the color-keyed collar rim is rough, and a pale gap opens at the -8 degree stress pose. A two-pixel original skin rim stays with the collar to reduce pinholes; it is not newly drawn hidden anatomy. Larger tilt tests FAIL visual acceptance even though the mesh has no foldovers. The authored narration shot uses only -1.1 to +1.4 degrees. The 4.8125-second normal and muted quarter-speed films are review studies, not approval of that smaller range. Full-resolution stills/component exports were inspected; no claim of listening verification or continuous movie playback is made.

This route is retained as a diagnostic construction candidate, not a clean neck repair. Do not increase tilt range or replace approved/default assets with it. Next: redraw a registered continuous neck and collar opening with deliberate overlap and clean outlines, then rerun the same tilt/word tests. Further raster dilation was rejected because it grew hair/outline colors outside the neck.

The F/V contact remains simplified; pointing-hand linework/wrist contour and shoulder creases remain unfinished. Legs are static and eyes have no blink rig. Exact phone boundaries remain unverified after the existing 18-region visual evidence review; this change does not alter speech timing. An artist/animator is still needed to finish construction and performance. CPU rendering limits iteration speed; faster hardware cannot supply missing drawings. Main, V3/V4, approved updater and native Moho files were preserved.
