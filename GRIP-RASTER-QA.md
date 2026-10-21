# ROVOR non-Moho raster wrist silhouette QA

**Goal.** The existing original-source Evan FK solution from draft PR #20 can
place a mathematical wrist pivot at a roller handle in both 1080p60 formats,
yet still pass when the outgoing actor frame is transparent at the wrist.
This draft adds a cheap, actual-image occupancy check in the standalone
renderer *before* sending RGB frames into FFmpeg.

## What it checks

In `evan-engine/grip_raster_qa.py`, each selected right-hand grip frame uses
the exact original `body-rig/manifest.json` and experimental registered
`hand-source/manifest.json` wrist geometry plus the **already applied**
shoulder/elbow/wrist controls and `body_roll` to locate Evan's wrist in the
real 1464x1536 source raster. It samples a small, 12-source-pixel-radius
disk around the attachment point and requires at least six actual pixels
with alpha >= 24. This samples directly with `getpixel`, avoiding copying
the entire source image's alpha plane for each long-form frame.

Before accepting the pixels, the gate requires the authentic source frame
size and RGBA mode, exact derived FK joint controls (not an old cached frame
with unrelated angles), and the registered relaxed-right source metadata.
It cannot silently substitute a generic avatar or an empty RGBA sprite.

`render_acting_video.py` invokes the check on the exact original body
image that it is about to use for **both** portrait and landscape directed
compositions. The two views share a source body, so the wrist check is run
only once per video frame, not twice. As in PR #20, body cache is disabled
for shots with changed FK gripping controls; the loop refuses unsafe
unadjusted actuation values. Completed chunk progress records
`realOriginalWristRasterFramesChecked`, while
`fingerCurlArtistApproved` remains deliberately false.

Shots without `handGripConstraints` incur only a trivial no-op and retain
the original non-Moho output behavior. No 24fps retiming, Moho dependency,
network calls, source-art overwrites, new model drawings, or audio
transformation are introduced.

## Evidence and limitations

The new three-platform GitHub Actions suite loads the *actual registered
original layered Evan artwork* and exercises `CartoonBody.render` with
solved FK angles. It then removes pixels around the wrist and requires the
quality gate to block that false connection. Tests also reject completely
transparent actor frames, uncorrected source controls, changed canvas
dimensions and missing hand registration, and rerun existing FK, physical
wall-contact, progressive paint and 1080p shot tests.

**Important:** A visible wrist-area alpha cluster is **not evidence of a
hand visibly wrapping the handle**. The sleeve alone may produce local
alpha. This module is a conservative technical check against missing art,
not a finger-curl mesh detector, original-scene aesthetic rating,
professional-animation acceptance or a finished MP4.

Before promoting the real painting film, obtain and visually approve
the authentic grip hand plate and roller/wall anchors; render at least
30 seconds with original narration in both 1080p60 compositions;
inspect arm/wrist/roller contact and actual paint appearance at normal
speed, and verify phoneme/lip sync and audio integrity.

Draft stack: PR #20 -> #19 -> #18 -> #14 -> #5. Do not independently
merge into main or claim live Moho 14 control.
