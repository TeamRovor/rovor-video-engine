"""Optional, source-art prop contact preflight for the 60fps directed scene renderer.

The same keyed layer transforms and camera model used by directed_scene.frame()
are sampled at every contact frame in *both* orientations. The source-art UV
anchors are explicitly authored; they are not inferred from a prompt or image
pixels. Their chosen source pixels must have actual nontransparent artwork.
This is a geometric safeguard, not proof of a hand bone, lip-sync,
physical simulation, rendered pixels, or artistic approval.
"""
import math


def _unit_pair(value, label):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(v) not in (float, int) or not math.isfinite(v)
                   or not 0 <= v <= 1 for v in value)):
        raise ValueError(label + ": expected normalized [u, v] coordinates")
    return tuple(float(v) for v in value)


def _part(value, label, allow_segment=False):
    if not isinstance(value, dict) or not isinstance(value.get("assetId"), str):
        raise ValueError(label + ": missing assetId")
    aid = value["assetId"]
    if not aid.strip():
        raise ValueError(label + ": blank assetId")
    point = "uv" in value
    segment = "segment" in value
    if point == segment or (segment and not allow_segment):
        raise ValueError(label + ": expected exactly one " +
                         ("uv point or segment" if allow_segment else "uv point"))
    if point:
        return aid, "point", (_unit_pair(value["uv"], label + ".uv"),)
    v = value["segment"]
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(label + ": expected a two-point segment")
    a, b = (_unit_pair(v[0], label + ".segment[0]"),
            _unit_pair(v[1], label + ".segment[1]"))
    if a == b:
        raise ValueError(label + ": zero-length segment")
    return aid, "segment", (a, b)


def _screen_xy(item, uv, frame, camera, canvas, size, interpolate):
    """Match frame()'s sprite center/scale/clockwise screen rotation.

    The image is sized in source pixels and positioned in the camera-adjusted
    canvas. PIL expands a rotated image around the same center, so this point
    transform is accurate up to sprite raster rounding/subpixel sampling.
    """
    width, height = canvas
    k = interpolate(item["keys"], frame)
    cam = interpolate(camera, frame)
    zoom = cam["zoom"]
    sw = max(2, round(size[0] * k["scale"] * zoom))
    sh = max(2, round(size[1] * k["scale"] * zoom))
    center_x = round((k["x"] - .5) * width * zoom + width * (.5 - cam["panX"]))
    center_y = round((k["y"] - .5) * height * zoom + height * (.5 - cam["panY"]))
    dx, dy = (uv[0] - .5) * sw, (uv[1] - .5) * sh
    theta = math.radians(k["rotation"])
    c, s = math.cos(theta), math.sin(theta)
    return (center_x + dx * c - dy * s, center_y + dx * s + dy * c), k["opacity"]


def _source_visible(image, uv):
    """Check the actual registered RGBA plate rather than an invented anchor."""
    w, h = image.size
    x, y = round(uv[0] * (w - 1)), round(uv[1] * (h - 1))
    return image.getpixel((x, y))[3] >= 8


def _point_segment_distance(point, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    length2 = vx * vx + vy * vy
    if length2 < 1e-9:
        return math.hypot(point[0] - a[0], point[1] - a[1]), 0.
    t = max(0., min(1., ((point[0] - a[0]) * vx + (point[1] - a[1]) * vy) / length2))
    return math.hypot(point[0] - a[0] - t * vx,
                      point[1] - a[1] - t * vy), t


def audit(shot, compositions, artwork, canvases, actor_id, interpolate):
    """Reject authored contact promises that disconnect during the shot.

    contactConstraints: [{"startFrame": 0, "endFrameExclusive": 60,
      "tool": {"assetId": "paint-roller", "uv": [.5, .05]},
      "target": {"assetId": "wall", "segment": [[.0, .0], [.0, 1.0]]},
      "maxGapPx": 12}]

    Contact coordinates refer to the bounds of registered original PNGs, not
    invented world positions. Rigged actor/hand anchors need a separate tested
    skeletal joint contract, so they are expressly unsupported here.
    """
    raw = shot.get("contactConstraints", [])
    required = shot.get("requirePhysicalContacts", False)
    if not isinstance(required, bool):
        raise ValueError("requirePhysicalContacts must be boolean")
    if not isinstance(raw, list) or len(raw) > 12:
        raise ValueError("contactConstraints must be a list of at most 12")
    if required and not raw:
        raise ValueError("Required physical prop contact was not specified")
    output = []
    for index, rule in enumerate(raw, 1):
        label = "Contact " + str(index)
        if not isinstance(rule, dict):
            raise ValueError(label + ": expected an object")
        begin, end = rule.get("startFrame"), rule.get("endFrameExclusive")
        if (type(begin) is not int or type(end) is not int
                or not shot["startFrame"] <= begin < end <= shot["endFrameExclusive"]):
            raise ValueError(label + ": invalid contact frame interval")
        gap = rule.get("maxGapPx")
        if type(gap) not in (int, float) or not math.isfinite(gap) or not 0 < gap <= 32:
            raise ValueError(label + ": maxGapPx must be 0 < pixels <= 32")
        tool_id, _, tool_uvs = _part(rule.get("tool"), label + ".tool")
        target_id, target_kind, target_uvs = _part(rule.get("target"), label + ".target", True)
        if tool_id == target_id or actor_id in (tool_id, target_id):
            raise ValueError(label + ": use distinct registered original prop layers; actor rig anchors are not supported")
        if tool_id not in artwork or target_id not in artwork:
            raise ValueError(label + ": both contact art assets must be registered")
        if not _source_visible(artwork[tool_id], tool_uvs[0]):
            raise ValueError(label + ": transparent artwork anchor on tool plate")
        if target_kind == "point" and not _source_visible(artwork[target_id], target_uvs[0]):
            raise ValueError(label + ": transparent artwork anchor on target plate")
        tested = {}
        for view, canvas in canvases.items():
            comp = compositions[view]
            indexed = {}
            for element in comp["elements"]:
                indexed.setdefault(element["assetId"], []).append(element)
            if len(indexed.get(tool_id, [])) != 1 or len(indexed.get(target_id, [])) != 1:
                raise ValueError(label + ": " + view + " requires exactly one layer of each contact asset")
            a, b = indexed[tool_id][0], indexed[target_id][0]
            worst_gap = -1.
            worst_frame = begin
            for frame in range(begin, end):
                tip, visible_a = _screen_xy(a, tool_uvs[0], frame, comp["camera"],
                                             canvas, artwork[tool_id].size, interpolate)
                target = []
                visible_b = 1.
                for uv in target_uvs:
                    point, visible_b = _screen_xy(b, uv, frame, comp["camera"],
                                                  canvas, artwork[target_id].size, interpolate)
                    target.append(point)
                if visible_a <= 0 or visible_b <= 0:
                    raise ValueError(label + ": invisible contact asset in " +
                                     view + " at frame " + str(frame))
                if target_kind == "point":
                    distance = math.hypot(tip[0] - target[0][0], tip[1] - target[0][1])
                else:
                    distance, t = _point_segment_distance(tip, target[0], target[1])
                    source_uv = tuple(p + t * (q - p) for p, q in zip(target_uvs[0], target_uvs[1]))
                    if not _source_visible(artwork[target_id], source_uv):
                        raise ValueError(label + ": transparent artwork anchor on target edge in " +
                                         view + " at frame " + str(frame))
                if distance > worst_gap:
                    worst_gap, worst_frame = distance, frame
                if distance > gap + 1e-9:
                    raise ValueError(label + ": detached " + view + " prop at frame " +
                                     str(frame) + " (" + format(distance, ".2f") +
                                     "px > " + format(gap, ".2f") + "px)")
            tested[view] = {"framesChecked": end - begin,
                            "maximumMeasuredGapPx": round(worst_gap, 3),
                            "worstFrame": worst_frame}
        output.append({"contactIndex": index, "startFrame": begin,
                       "endFrameExclusive": end, "maxAllowedGapPx": float(gap),
                       "targetKind": target_kind, "views": tested})
    return {"constraintsChecked": len(output), "details": output,
            "artisticApproval": False, "actorHandRigValidated": False}
