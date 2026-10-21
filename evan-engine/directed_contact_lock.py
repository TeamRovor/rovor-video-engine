"""Actual 60fps prop-contact motion for ROVOR's non-Moho original-art renderer.

Existing authored sprite motion supplies the gesture along a real wall edge.
An opt-in contact lock removes ONLY perpendicular drift by moving the prop's
source-art UV anchor onto the nearest opaque target point/segment every frame.
Both orientations use their own calibrated artwork/camera/keyframe geometry.

The locked motion becomes the real frame() animation keys, then passes the
existing independent contact audit; it is not an unrendered compliance claim.
It cannot move Evan's actual hand or replace a production articulated rig.
"""
from __future__ import annotations
import math

from directed_contact import (_part, _screen_xy, _source_visible,
                              _point_segment_distance)

MAX_LOCKED_RULES = 12
MAX_CORRECTION_PIXELS = 260.
BOUNDARY_JUMP_PIXELS = 28.


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _target_point(rule, frame, target_layer, camera, canvas, artwork,
                  interpolate):
    target_id, kind, uvs = rule["target_data"]
    coords = []
    target_alpha = 1.
    for uv in uvs:
        xy, target_alpha = _screen_xy(
            target_layer, uv, frame, camera, canvas,
            artwork[target_id].size, interpolate)
        coords.append(xy)
    if target_alpha <= 0:
        raise ValueError("Invisible target while physically locked")
    if kind == "point":
        uv = uvs[0]
        if not _source_visible(artwork[target_id], uv):
            raise ValueError("Locked target UV is transparent")
        return coords[0]
    authored_tip, _ = _screen_xy(
        rule["tool_layer"], rule["tool_uv"], frame, camera, canvas,
        artwork[rule["tool_id"]].size, interpolate)
    _, t = _point_segment_distance(authored_tip, coords[0], coords[1])
    source_uv = tuple(a + t * (b - a) for a, b in zip(uvs[0], uvs[1]))
    if not _source_visible(artwork[target_id], source_uv):
        raise ValueError("Locked target edge has no visible artwork at contact")
    return (coords[0][0] + t * (coords[1][0] - coords[0][0]),
            coords[0][1] + t * (coords[1][1] - coords[0][1]))


def _lock_rules(shot, comp, view, artwork, actor_id):
    constraints = shot.get("contactConstraints", [])
    if not isinstance(constraints, list):
        # The canonical audit validates the same incoming schema.
        return []
    locks = []
    for n, entry in enumerate(constraints, 1):
        if not isinstance(entry, dict):
            continue
        locking = entry.get("lockToolToTarget", False)
        if type(locking) is not bool:
            raise ValueError("Contact %d: lockToolToTarget must be boolean" % n)
        if not locking:
            continue
        start, end = entry.get("startFrame"), entry.get("endFrameExclusive")
        if (type(start) is not int or type(end) is not int or
                not shot["startFrame"] <= start < end <= shot["endFrameExclusive"]):
            raise ValueError("Contact %d: invalid lock interval" % n)
        tool_id, tool_kind, tool_uvs = _part(entry.get("tool"), "Lock.tool")
        target_id, _, _ = _part(entry.get("target"), "Lock.target", True)
        if tool_id == target_id or actor_id in (tool_id, target_id):
            raise ValueError("Prop locks need distinct real original-art assets, not actor hand coordinates")
        if tool_id not in artwork or target_id not in artwork:
            raise ValueError("Locked contact assets must be registered original artwork")
        by_id = {}
        for element in comp["elements"]:
            by_id.setdefault(element["assetId"], []).append(element)
        if len(by_id.get(tool_id, [])) != 1 or len(by_id.get(target_id, [])) != 1:
            raise ValueError("Ambiguous tool or target layer in " + view)
        tool = by_id[tool_id][0]
        target = by_id[target_id][0]
        if not _source_visible(artwork[tool_id], tool_uvs[0]):
            raise ValueError("Transparent tool contact anchor")
        corr = entry.get("maxCorrectionPx", MAX_CORRECTION_PIXELS)
        if (type(corr) not in (int, float) or not math.isfinite(corr)
                or not 0 < corr <= MAX_CORRECTION_PIXELS):
            raise ValueError("maxCorrectionPx must be within 0..260")
        locks.append({
            "n": n, "start": start, "end": end,
            "tool_id": tool_id, "target_id": target_id,
            "tool_layer": tool, "target_layer": target,
            "tool_uv": tool_uvs[0],
            "target_data": _part(entry["target"], "Lock.target", True),
            "max_correction": float(corr),
        })
    if len(locks) > MAX_LOCKED_RULES:
        raise ValueError("Too many active physical contact locks")
    by_tool = {}
    for r in locks:
        by_tool.setdefault(r["tool_id"], []).append(r)
    for tool, entries in by_tool.items():
        for earlier, later in zip(sorted(entries, key=lambda z: z["start"]),
                                  sorted(entries, key=lambda z: z["start"])[1:]):
            if earlier["end"] > later["start"]:
                raise ValueError("Overlapping contact locks for tool " + tool)
    return locks


def _locked_key(rule, base, frame, comp, artwork, canvas, interpolate):
    camera = comp["camera"]
    original_point, visible = _screen_xy(rule["tool_layer"], rule["tool_uv"],
                                         frame, camera, canvas,
                                         artwork[rule["tool_id"]].size, interpolate)
    if visible <= 0:
        raise ValueError("Invisible moving tool during locked contact")
    wanted = _target_point(rule, frame, rule["target_layer"], camera,
                           canvas, artwork, interpolate)
    displacement = _distance(original_point, wanted)
    if displacement > rule["max_correction"] + 1e-8:
        raise ValueError("Contact %d: authored tool too far from target at frame %d (%.1fpx)"
                         % (rule["n"], frame, displacement))
    zoom = interpolate(camera, frame)["zoom"]
    nx = base["x"] + (wanted[0] - original_point[0]) / (canvas[0] * zoom)
    ny = base["y"] + (wanted[1] - original_point[1]) / (canvas[1] * zoom)
    if not (0 <= nx <= 1 and 0 <= ny <= 1):
        raise ValueError("Locked prop placement exceeds normal stage bounds")
    out = dict(base, x=nx, y=ny)
    # Integer rasterization is part of the actual renderer. A lock must be
    # enforceable with its real center rounding and image dimensions.
    virtual = dict(rule["tool_layer"],
                   keys=[(frame, out, "linear")])
    actual, _ = _screen_xy(virtual, rule["tool_uv"], frame, camera, canvas,
                          artwork[rule["tool_id"]].size, interpolate)
    if _distance(actual, wanted) > 1.45:
        raise ValueError("Locked prop raster position could not track the target")
    return out


def apply_locked_contacts(shot, compositions, artwork, canvases,
                          actor_id, interpolate):
    """Return new composition dictionaries with physically solved sprite keys.

    This samples each tool at actual integer video frames, using the original
    authored track as the desired movement parallel to the target segment.
    Original source tracks remain intact; existing scenes without opt-in locks
    return exactly the original objects. This happens before standard preflight
    so the existing geometry audit measures the *rendered* locked keys.
    """
    copies = dict(compositions)
    detail = {}
    for view, comp in compositions.items():
        rules = _lock_rules(shot, comp, view, artwork, actor_id)
        if not rules:
            continue
        by_tool = {}
        for rule in rules:
            by_tool.setdefault(rule["tool_id"], []).append(rule)
        new_comp = dict(comp)
        elements = []
        canvas = canvases[view]
        for element in comp["elements"]:
            rs = by_tool.get(element["assetId"])
            if not rs:
                elements.append(element)
                continue
            old_keys = element["keys"]
            new_keys = []
            old_center = lambda f, uv: _screen_xy(
                element, uv, f, comp["camera"], canvas,
                artwork[element["assetId"]].size, interpolate)[0]
            # Include shot-end as the original stage key; cuts are the scene
            # boundary and any new shot owns its own first setup key.
            for f in range(shot["startFrame"], shot["endFrameExclusive"] + 1):
                base = interpolate(old_keys, f)
                active = next((r for r in rs if r["start"] <= f < r["end"]), None)
                new = (_locked_key(active, base, f, comp, artwork, canvas, interpolate)
                       if active else base)
                new_keys.append((f, new, "linear"))
            new_layer = dict(element, keys=new_keys)
            # Smooth approach and release must already be storyboarded.
            # Never hide a one-frame teleport with a silent auto-snap.
            for rule in rs:
                start, end = rule["start"], rule["end"]
                if start > shot["startFrame"]:
                    before = old_center(start - 1, rule["tool_uv"])
                    locked_at = _screen_xy(new_layer, rule["tool_uv"], start,
                                           comp["camera"], canvas,
                                           artwork[rule["tool_id"]].size, interpolate)[0]
                    if _distance(before, locked_at) > BOUNDARY_JUMP_PIXELS:
                        raise ValueError("Contact %d: abrupt lock entrance in %s at frame %d"
                                         % (rule["n"], view, start))
                if end < shot["endFrameExclusive"]:
                    last = _screen_xy(new_layer, rule["tool_uv"], end - 1,
                                      comp["camera"], canvas,
                                      artwork[rule["tool_id"]].size, interpolate)[0]
                    after = old_center(end, rule["tool_uv"])
                    if _distance(last, after) > BOUNDARY_JUMP_PIXELS:
                        raise ValueError("Contact %d: abrupt lock release in %s at frame %d"
                                         % (rule["n"], view, end))
            elements.append(new_layer)
        new_comp["elements"] = elements
        copies[view] = new_comp
        detail[view] = {"lockedConstraints": len(rules),
                        "frameSamples": sum(r["end"] - r["start"] for r in rules)}
    return copies, detail
