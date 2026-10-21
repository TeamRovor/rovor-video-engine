"""Ground non-Moho tool grips in Evan's *real original* arm FK geometry.

No invented "hand center" image guesses: the arm is the published
CartoonBody source rig, whose right forearm uses the source shoulder/elbow,
and whose selected relaxed-hand plate uses hand-source rigWrist. The same
resolved shoulder/elbow angles render in BOTH 60fps views.

This solver does not redraw fingers, prove a closed hand, or imply visual
approval of the experimental source rig. Fail closed if target cannot be
reached within existing 12/30-degree acting joint limits and both views.
"""
from __future__ import annotations
import math

from directed_contact import _screen_xy, _source_visible, _unit_pair
from directed_paint import _source_pixel

ACTOR_SIZE = (1464, 1536)
ACTOR_PAD_X = 220
BODY_PIVOT = (732, 950)
MAX_VIEW_DISAGREEMENT_SOURCE_PX = 5.
MAX_SPEED_DEG_PER_FRAME = 2.5
MAX_SOURCE_ERROR_PX = 6.5
JOINT_LIMITS = (12., 30.)
MAX_SOLVER_STEPS = 26


def _point(v, name):
    if (not isinstance(v, (list, tuple)) or len(v) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in v)
            or not all(0 <= x <= 1536 for x in v)):
        raise ValueError("Invalid original FK rig joint " + name)
    return tuple(float(x) for x in v)


def _rotate(point, pivot, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    x, y = point[0] - pivot[0], point[1] - pivot[1]
    return pivot[0] + x * c - y * s, pivot[1] + x * s + y * c


def wrist_xy(meta, hand_meta, angles):
    """Match the source arm_transforms forearm wrist attachment.

    CartoonBody uses hand-source's rigWrist for the selected relaxed plate.
    The terminal wrist angle rotates the hand about this point, so it
    doesn't move the attachment itself; only shoulder/elbow move it.
    """
    if len(angles) != 3 or any(type(x) not in (int, float) or not math.isfinite(x)
                               for x in angles):
        raise ValueError("Invalid authored right-arm FK controls")
    right = meta["arms"]["right"]
    shoulder = _point(right["shoulder"], "shoulder")
    elbow = _point(right["elbow"], "elbow")
    wrist = _point(hand_meta["relaxed-right"]["rigWrist"], "relaxed wrist")
    first = _rotate(elbow, shoulder, angles[0])
    local_wrist = _rotate(wrist, elbow, angles[1])
    return _rotate(local_wrist, shoulder, angles[0])


def _inside_canvas_wrist(xy, body_roll):
    """Apply actual CartoonBody 1464x1536 pose and PIL body_roll.

    PIL positive rotate is CCW in screen space; source arm FK positive
    angles are clockwise in y-down screen coordinates.
    """
    source = (xy[0] + ACTOR_PAD_X, xy[1])
    center = BODY_PIVOT
    return _rotate(source, center, -body_roll)


def _body_local_target(screen, actor, frame, comp, canvas, interpolate, roll):
    uv, _ = _source_pixel(screen, actor, frame, comp["camera"],
                          canvas, ACTOR_SIZE, interpolate)
    pixel = uv[0] * ACTOR_SIZE[0], uv[1] * ACTOR_SIZE[1]
    if not all(math.isfinite(v) for v in pixel):
        raise ValueError("Nonfinite grip target")
    undone = _rotate(pixel, BODY_PIVOT, roll)
    return undone[0] - ACTOR_PAD_X, undone[1]


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _solve(meta, hand_meta, authored, wanted, previous=None):
    """Damped two-joint FK correction, limits identical to performance_tracks.

    No actor translation, fake body scale, or 24fps key conversion.
    Only two real original arm joints are solved; the wrist-angle stays
    authored, preserving the actual relaxed-hand plate pose/roll.
    """
    base = (float(authored[0]), float(authored[1]))
    a, b = previous[:2] if previous is not None else base
    # The source pose is near fully extended; inverse kinematics has two
    # mathematical elbow branches. Keep the previous real pose as the
    # continuity constraint instead of allowing flips between those branches.
    alow, ahigh = -JOINT_LIMITS[0], JOINT_LIMITS[0]
    blow, bhigh = -JOINT_LIMITS[1], JOINT_LIMITS[1]
    if previous is not None:
        alow = max(alow, previous[0] - MAX_SPEED_DEG_PER_FRAME)
        ahigh = min(ahigh, previous[0] + MAX_SPEED_DEG_PER_FRAME)
        blow = max(blow, previous[1] - MAX_SPEED_DEG_PER_FRAME)
        bhigh = min(bhigh, previous[1] + MAX_SPEED_DEG_PER_FRAME)
    for _ in range(MAX_SOLVER_STEPS):
        point = wrist_xy(meta, hand_meta, (a, b, authored[2]))
        ex, ey = wanted[0] - point[0], wanted[1] - point[1]
        if math.hypot(ex, ey) < .0001:
            break
        # Exact analytic derivative d position / d degrees, using the
        # original hierarchical shoulder and elbow pivots.
        shoulder = _point(meta["arms"]["right"]["shoulder"], "shoulder")
        elbow = _rotate(_point(meta["arms"]["right"]["elbow"], "elbow"),
                        shoulder, a)
        radians = math.pi / 180
        j11, j21 = -(point[1] - shoulder[1]) * radians, (point[0] - shoulder[0]) * radians
        j12, j22 = -(point[1] - elbow[1]) * radians, (point[0] - elbow[0]) * radians
        damp = .80
        aa = j11*j11 + j21*j21 + damp
        ab = j11*j12 + j21*j22
        bb = j12*j12 + j22*j22 + damp
        v1, v2 = j11*ex + j21*ey, j12*ex + j22*ey
        det = aa*bb - ab*ab
        if det <= 0:
            raise ValueError("Original FK arm singularity")
        da = (bb*v1-ab*v2)/det
        db = (aa*v2-ab*v1)/det
        a = max(alow, min(ahigh, a + max(-.75, min(.75, da))))
        b = max(blow, min(bhigh, b + max(-.75, min(.75, db))))
    output = (a, b, float(authored[2]))
    error = _distance(wrist_xy(meta, hand_meta, output), wanted)
    if error > MAX_SOURCE_ERROR_PX:
        raise ValueError("Original FK wrist cannot reach tool handle inside safe joint limits (%.2f source px)" % error)
    return output


def solve_grips(shot, compositions, images, canvases, actor_id,
                interpolate, performance, rig_meta, hand_meta):
    """Compute shared original body FK overrides and view-by-view evidence.

    Production renderer uses the returned per-frame controls for both
    orientations; by design there is only one actual Evan body per frame.
    """
    entries = shot.get("handGripConstraints", [])
    if not isinstance(entries, list) or len(entries) > 2:
        raise ValueError("handGripConstraints must be a list of at most two")
    if not entries:
        return {}, {"gripsChecked": 0, "artisticApproval": False,
                    "realGripFingersValidated": False}
    if performance is None or not isinstance(rig_meta, dict) or not isinstance(hand_meta, dict):
        raise ValueError("Actual original FK performance and source rig manifests required for hand grip")
    if hand_meta.get("visualApproved") is True:
        # The hand-source metadata is experimental, not authorized as a
        # fingerprinted and visually approved closed-grip animation.
        raise ValueError("Unexpected hand-source approval metadata; inspect actual rig")
    if "relaxed-right" not in hand_meta or "arms" not in rig_meta:
        raise ValueError("Missing original relaxed-right source plate and FK arm geometry")
    controls = {}
    evidence = []
    for n, rule in enumerate(entries, 1):
        if not isinstance(rule, dict) or set(rule) != {
            "startFrame", "endFrameExclusive", "toolAssetId",
            "toolHandleUV", "hand", "maxGripGapPx"}:
            raise ValueError("Grip %d: exact source-anchored grip schema required" % n)
        first, last = rule["startFrame"], rule["endFrameExclusive"]
        if (type(first) is not int or type(last) is not int or
                not shot["startFrame"] <= first < last <= shot["endFrameExclusive"]):
            raise ValueError("Grip %d: invalid shot frame interval" % n)
        if rule["hand"] != "relaxed-right":
            raise ValueError("Only registered original relaxed-right hand may be used pending grip-art approval")
        tool_id = rule["toolAssetId"]
        uv = _unit_pair(rule["toolHandleUV"], "Grip %d handle UV" % n)
        tolerance = rule["maxGripGapPx"]
        if (type(tolerance) not in (int, float) or not math.isfinite(tolerance)
                or not 0 < tolerance <= 8):
            raise ValueError("Grip tolerance must be 0..8 screen pixels")
        if tool_id not in images or tool_id == actor_id:
            raise ValueError("Grip tool must be original registered distinct art")
        if not _source_visible(images[tool_id], uv):
            raise ValueError("Grip tool handle UV must be on drawn opaque original art")
        worst = {view: 0. for view in canvases}
        last_angles = None
        for frame in range(first, last):
            if frame in controls:
                raise ValueError("Overlapping grip constraints on the same real original right wrist")
            base = performance.at_frame(frame)
            if base.get("right_hand") != "relaxed":
                raise ValueError("Original FK hand pose is not relaxed at frame %d" % frame)
            if (not isinstance(base.get("right"), (list, tuple)) or len(base["right"]) != 3
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in base["right"])):
                raise ValueError("Invalid original right shoulder/elbow/wrist performance")
            roll = base.get("body_roll", 0.)
            if type(roll) not in (int, float) or not math.isfinite(roll) or abs(roll) > 1.5:
                raise ValueError("Body roll outside original joint limits")
            local_wanted = []
            view_items = []
            for view, comp in compositions.items():
                indexed = {}
                for i, item in enumerate(comp["elements"]):
                    indexed.setdefault(item["assetId"], []).append((i, item))
                if len(indexed.get(actor_id, [])) != 1 or len(indexed.get(tool_id, [])) != 1:
                    raise ValueError("Grip needs precisely one original actor and tool per composition")
                actor_index, actor = indexed[actor_id][0]
                tool_index, tool = indexed[tool_id][0]
                if actor_index >= tool_index:
                    raise ValueError("Grip tool must composite in front of the original actor")
                tip, opacity = _screen_xy(tool, uv, frame, comp["camera"],
                                         canvases[view], images[tool_id].size, interpolate)
                if opacity <= 0:
                    raise ValueError("Grip handle invisible in " + view)
                local = _body_local_target(tip, actor, frame, comp, canvases[view],
                                           interpolate, roll)
                local_wanted.append(local)
                view_items.append((view, comp, actor, tip))
            if len(local_wanted) != 2 or _distance(*local_wanted) > MAX_VIEW_DISAGREEMENT_SOURCE_PX:
                raise ValueError("Portrait and landscape require incompatible grip targets for the one Evan skeleton")
            wanted = ((local_wanted[0][0] + local_wanted[1][0]) / 2.,
                      (local_wanted[0][1] + local_wanted[1][1]) / 2.)
            solution = _solve(rig_meta, hand_meta, base["right"], wanted,
                              previous=last_angles)
            if (last_angles is not None and any(
                    abs(a - b) > MAX_SPEED_DEG_PER_FRAME
                    for a, b in zip(last_angles[:2], solution[:2]))):
                raise ValueError("Solved real FK hand jumps too far between adjacent 60fps frames")
            last_angles = solution
            transformed_wrist = _inside_canvas_wrist(
                wrist_xy(rig_meta, hand_meta, solution), roll)
            for view, comp, actor, tip in view_items:
                projected, visible = _screen_xy(
                    actor, (transformed_wrist[0] / ACTOR_SIZE[0],
                            transformed_wrist[1] / ACTOR_SIZE[1]),
                    frame, comp["camera"], canvases[view],
                    ACTOR_SIZE, interpolate)
                if visible <= 0:
                    raise ValueError("Invisible original Evan during tool grip")
                gap = _distance(projected, tip)
                if gap > tolerance:
                    raise ValueError("Real FK wrist detached from tool handle in %s at frame %d (%.2fpx)" %
                                     (view, frame, gap))
                worst[view] = max(worst[view], gap)
            controls[frame] = solution
        evidence.append({
            "gripIndex": n, "startFrame": first, "endFrameExclusive": last,
            "framesChecked": last - first,
            "viewMaxMeasuredGapPx": {v: round(d, 4) for v, d in worst.items()},
            "humanHandGripVisuallyApproved": False,
            "fingerCurlRigVerified": False
        })
    return controls, {
        "gripsChecked": len(evidence),
        "details": evidence,
        "artisticApproval": False,
        "realGripFingersValidated": False,
        "sourceRig": "original-evan-layered",
    }
