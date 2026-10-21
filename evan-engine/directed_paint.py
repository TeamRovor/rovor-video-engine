"""Persistent paint deposited by contact-locked original-art props, without Moho.

Paint is expressed in the WALL'S source-image coordinates. Every 60fps roller
anchor is inverse-projected through the actual target transform/camera and
rasterized onto a paint mask clipped to original target alpha and an authored
region. Thus painted coverage stays on a moving/rotating wall, persists after
the roller leaves, and never appears before the motion that created it.

A bounded incremental renderer avoids re-rasterizing previous strokes on
sequential frames; random frame seeks reset/replay from source points. No
source PNG changes, private media, external art, shell, or network calls.
"""
from __future__ import annotations

import math
from PIL import Image, ImageColor, ImageDraw, ImageChops
from directed_contact import _part, _screen_xy, _source_visible


def _region(v):
    if (not isinstance(v, list) or len(v) != 4
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in v)
            or not (0 <= v[0] < v[2] <= 1 and 0 <= v[1] < v[3] <= 1)):
        raise ValueError("paintStroke.regionUV must be [left, top, right, bottom] in 0..1")
    return tuple(float(x) for x in v)


def _source_pixel(screen, layer, frame, camera, canvas, source_size, interpolate):
    """Inverse of directed_contact._screen_xy including camera/rotation."""
    width, height = canvas
    k = interpolate(layer["keys"], frame)
    cam = interpolate(camera, frame)
    zoom = cam["zoom"]
    iw = max(2, round(source_size[0] * k["scale"] * zoom))
    ih = max(2, round(source_size[1] * k["scale"] * zoom))
    center_x = round((k["x"] - .5) * width * zoom + width * (.5 - cam["panX"]))
    center_y = round((k["y"] - .5) * height * zoom + height * (.5 - cam["panY"]))
    theta = math.radians(k["rotation"])
    c, s = math.cos(theta), math.sin(theta)
    dx, dy = screen[0] - center_x, screen[1] - center_y
    local_x, local_y = dx * c + dy * s, -dx * s + dy * c
    u, v = .5 + local_x / iw, .5 + local_y / ih
    return (u, v), (round(u * (source_size[0] - 1)),
                     round(v * (source_size[1] - 1)))


class PaintTrack:
    """Deterministic incremental mask, safe for out-of-order frame seeks."""

    def __init__(self, base, points, start, end, rgb, radius, bounds):
        self.base = base
        self.points = tuple(points)
        self.start, self.end = start, end
        self.color = tuple(rgb)
        self.radius = radius
        self.bounds = bounds
        self.mask = Image.new("L", base.size)
        self.draw = ImageDraw.Draw(self.mask)
        self.count = 0
        self.last_frame = None
        self.last_image = None
        # Source RGBA alpha clips paint even where the circle brushes toward
        # invisible PNG padding. The rectangular region is independently
        # authored and is also not permitted to spill outside the source.
        region = Image.new("L", base.size)
        x0, y0, x1, y1 = bounds
        ImageDraw.Draw(region).rectangle((x0, y0, x1, y1), fill=255)
        self.allowed_mask = ImageChops.multiply(base.getchannel("A"), region)
        self.finished_image = None

    def _restart(self):
        self.mask = Image.new("L", self.base.size)
        self.draw = ImageDraw.Draw(self.mask)
        self.count = 0
        self.last_frame = None
        self.last_image = None

    def source_at(self, frame):
        if frame < self.start:
            return self.base
        if frame >= self.end and self.finished_image is not None:
            return self.finished_image
        upto = min(frame - self.start + 1, len(self.points))
        if upto < self.count:
            self._restart()
        if self.count == upto and self.last_image is not None:
            return self.last_image
        rad = self.radius
        for i in range(self.count, upto):
            x, y = self.points[i]
            if i:
                self.draw.line((self.points[i - 1], self.points[i]),
                               fill=255, width=2 * rad + 1)
            self.draw.ellipse((x - rad, y - rad, x + rad, y + rad), fill=255)
        self.count = upto
        clipped = ImageChops.multiply(self.mask, self.allowed_mask)
        color = Image.new("RGBA", self.base.size, (*self.color, 0))
        color.putalpha(clipped)
        self.last_image = Image.alpha_composite(self.base, color)
        self.last_frame = frame
        if frame >= self.end or upto == len(self.points):
            self.finished_image = self.last_image
        return self.last_image


def prepare_paint_tracks(shot, compositions, images, canvases,
                         actor_id, interpolate):
    """Preflight every paint sample and return actual render-side paint tracks.

    Require physical contact lock already solved (called after contact audit).
    One source target per shot keeps paint masks non-overlapping and
    side-effect-free; extra target layers need their own shots.
    """
    trails = {view: {} for view in canvases}
    evidence = {}
    constraints = shot.get("contactConstraints", [])
    for index, rule in enumerate(constraints, 1):
        if not isinstance(rule, dict) or "paintStroke" not in rule:
            continue
        if rule.get("lockToolToTarget") is not True:
            raise ValueError("Paint %d: visible paint requires locked actual tool contact" % index)
        spec = rule["paintStroke"]
        if not isinstance(spec, dict) or set(spec) != {"color", "radiusSourcePx", "regionUV"}:
            raise ValueError("Paint %d: expected color/radiusSourcePx/regionUV" % index)
        color = spec["color"]
        if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
            raise ValueError("Paint %d: color must be exact #RRGGBB" % index)
        try:
            rgb = ImageColor.getrgb(color)
        except ValueError as exc:
            raise ValueError("Paint %d: invalid paint color" % index) from exc
        radius = spec["radiusSourcePx"]
        if type(radius) is not int or not 1 <= radius <= 24:
            raise ValueError("Paint %d: radiusSourcePx must be 1..24" % index)
        rgn = _region(spec["regionUV"])
        tool_id, tool_type, tool_uvs = _part(rule.get("tool"), "Paint.tool")
        target_id, _, _ = _part(rule.get("target"), "Paint.target", True)
        if tool_id == target_id or actor_id in (tool_id, target_id):
            raise ValueError("Paint strokes must use distinct original-art prop/target sprites")
        if tool_id not in images or target_id not in images:
            raise ValueError("Paint sprites must be registered original PNG art")
        start, end = rule.get("startFrame"), rule.get("endFrameExclusive")
        if (type(start) is not int or type(end) is not int
                or not shot["startFrame"] <= start < end <= shot["endFrameExclusive"]):
            raise ValueError("Paint contact interval must fit the current shot")
        evidence[index] = {}
        original = images[target_id]
        width, height = original.size
        bounds = (math.ceil(rgn[0] * (width - 1)), math.ceil(rgn[1] * (height - 1)),
                  math.floor(rgn[2] * (width - 1)), math.floor(rgn[3] * (height - 1)))
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            raise ValueError("Paint region too small for original artwork")
        for view, comp in compositions.items():
            if target_id in trails[view]:
                raise ValueError("Multiple independent paint strokes on same wall require a new shot")
            layers = comp["elements"]
            tools = [(n, a) for n, a in enumerate(layers) if a["assetId"] == tool_id]
            targets = [(n, a) for n, a in enumerate(layers) if a["assetId"] == target_id]
            if len(tools) != 1 or len(targets) != 1:
                raise ValueError("Paint contact needs one physical tool and one target in " + view)
            tool_order, tool = tools[0]
            target_order, target = targets[0]
            if target_order >= tool_order:
                raise ValueError("Paintable wall must render behind moving tool in " + view)
            points = []
            for frame in range(start, end):
                screen_tip, opacity = _screen_xy(tool, tool_uvs[0], frame,
                                                 comp["camera"], canvases[view],
                                                 images[tool_id].size, interpolate)
                if opacity <= 0:
                    raise ValueError("Invisible painting tool")
                uv, pixel = _source_pixel(screen_tip, target, frame, comp["camera"],
                                          canvases[view], original.size, interpolate)
                if not (rgn[0] <= uv[0] <= rgn[2] and rgn[1] <= uv[1] <= rgn[3]):
                    raise ValueError("Paint tip outside the authored painted-wall region in %s frame %d"
                                     % (view, frame))
                if not _source_visible(original, uv):
                    raise ValueError("Paint tip touches a transparent source-wall region")
                points.append(pixel)
            if len(set(points)) < 3:
                raise ValueError("Paint %d: no progressive stroke along target in %s"
                                 % (index, view))
            track = PaintTrack(original, points, start, end, rgb, radius, bounds)
            trails[view][target_id] = track
            evidence[index][view] = {
                "framesPainted": end - start,
                "distinctSourcePixels": len(set(points)),
                "paintColor": color,
                "renderedPixelVerificationRequired": True,
                "artisticApproval": False
            }
    return trails, evidence
