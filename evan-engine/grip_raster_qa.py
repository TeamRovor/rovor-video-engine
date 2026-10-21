"""Fast real-frame source-art wrist silhouette QA for ROVOR non-Moho render.

The previous FK verifier checked geometric wrist-to-handle positions, but
could not tell whether the rendered actor alpha was empty at that position.
Use the actual 1464x1536 CartoonBody.render RGBA *already about to be
composited*, and the actual registered relaxed-right source rigWrist.

This only proves visible RGBA art is present around the physical wrist
attachment. It does not prove fingers genuinely wrap the tool handle,
anatomical correctness, camera composition, or artistic approval.
"""
from __future__ import annotations

import math
from PIL import Image
from right_hand_grip import (_inside_canvas_wrist, wrist_xy, ACTOR_SIZE)

# This is a minimal local *silhouette* gate, not a human pose-quality metric.
SAMPLE_RADIUS_SOURCE_PX = 12
SAMPLE_STEP_SOURCE_PX = 3
MIN_OPAQUE_SAMPLES = 6
MIN_OPAQUE_ALPHA = 24


def _sample_coverage(image, center):
    cx, cy = center
    if not all(math.isfinite(v) for v in (cx, cy)):
        raise ValueError("Nonfinite rendered wrist location")
    if not (0 <= cx < image.width and 0 <= cy < image.height):
        raise ValueError("Real rendered wrist outside actor canvas")
    # Read only a tiny local disk. Avoid copying the entire 1464x1536
    # alpha channel on every frame of an eight-minute source narration.
    covered = 0
    total = 0
    radius = SAMPLE_RADIUS_SOURCE_PX
    for dy in range(-radius, radius + 1, SAMPLE_STEP_SOURCE_PX):
        for dx in range(-radius, radius + 1, SAMPLE_STEP_SOURCE_PX):
            if dx*dx + dy*dy > radius*radius:
                continue
            x, y = round(cx + dx), round(cy + dy)
            if not (0 <= x < image.width and 0 <= y < image.height):
                raise ValueError("Real wrist artwork clipped outside original actor canvas")
            total += 1
            if image.getpixel((x, y))[3] >= MIN_OPAQUE_ALPHA:
                covered += 1
    if covered < MIN_OPAQUE_SAMPLES:
        raise ValueError(
            "Original Evan wrist/hand is visually missing at grip "
            "(%d opaque local source pixels / %d sampled)" % (covered, total))
    return {"opaqueSamples": covered, "totalSamples": total,
            "wristArtworkPresent": True, "fingerCurlVerified": False,
            "studioApproved": False}


def check_frame(rendered_actor, frame, shot, controls, rig_meta, hand_meta):
    """Reject invisible original FK wrist art BEFORE submitting RGB to FFmpeg.

    No-op for scenes without a physical right-hand grip; per-frame 60fps
    geometry validation has already been performed during scene preflight.
    """
    grips = shot.get("gripControls", {})
    if not grips or frame not in grips:
        return None
    if (not isinstance(rendered_actor, Image.Image)
            or rendered_actor.mode != "RGBA" or rendered_actor.size != ACTOR_SIZE):
        raise ValueError("Grip requires actual RGBA original Evan 1464x1536 render")
    if (not isinstance(controls, dict) or "right" not in controls
            or "body_roll" not in controls):
        raise ValueError("Original Evan FK applied controls required for wrist raster QA")
    if controls.get("right_hand") != "relaxed":
        raise ValueError("Actual relaxed-right original hand plate required for grip frame")
    expected = grips[frame]
    if (len(expected) != 3 or len(controls["right"]) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in (*expected, *controls["right"]))
            or max(abs(a - b) for a, b in zip(expected, controls["right"])) > 1.e-5):
        raise ValueError("Cached or uncorrected original arm frame cannot satisfy grip QA")
    if ("relaxed-right" not in hand_meta
            or "right" not in rig_meta.get("arms", {})):
        raise ValueError("Missing authentic source arm/relaxed hand geometry")
    body_roll = controls["body_roll"]
    if (type(body_roll) not in (int, float)
            or not math.isfinite(body_roll) or abs(body_roll) > 1.5):
        raise ValueError("Invalid original Evan body roll")
    xy = _inside_canvas_wrist(wrist_xy(rig_meta, hand_meta, expected), body_roll)
    result = _sample_coverage(rendered_actor, xy)
    return {"frame": frame, "rasterWrist": [round(v, 3) for v in xy],
            **result}
