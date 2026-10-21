"""Pixel-grounded persistent wall paint after real roller motion, no Moho.

Source-free tests render real 1920x1080 and 1080x1920 Pillow RGB frames.
Test original PNGs are registered SHA-verified source fixture art, not the
user's genuine Evan painting assets or creative approval.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from directed_scene import DirectedScene, check, interpolate, SIZES
from directed_contact import _screen_xy
from test_directed_scene import fixture, key


PAINT = (230, 57, 70)
WALL = (134, 107, 82)


class VisiblePaintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config, self.registry = fixture(self.root)
        self.shot = self.config["shots"][0]
        self.actor = Image.new("RGBA", (280, 360), (0, 0, 0, 0))
        for view in SIZES:
            comp = self.shot["compositions"][view]
            wall = next(e for e in comp["elements"] if e["assetId"] == "desk")
            roller = next(e for e in comp["elements"] if e["assetId"] == "globe")
            wall["keys"] = [key(0, .5, .5, scale=.7),
                            key(480, .5, .5, scale=.7)]
            # Roller makes one up-and-down pass, then peels off the wall.
            # The source art remains unchanged and narration is not touched.
            roller["keys"] = [
                key(0, .5, .5, scale=.5),
                key(60, .5, .5, scale=.5),
                key(240, .5, .42, scale=.5),
                key(420, .5, .5, scale=.5),
                key(480, .5, .7, scale=.5)]
        self.rule = {
            "startFrame": 60, "endFrameExclusive": 420,
            "tool": {"assetId": "globe", "uv": [.5, .5]},
            "target": {"assetId": "desk", "segment": [[.5, .20], [.5, .8]]},
            "maxGapPx": 2,
            "maxCorrectionPx": 255,
            "lockToolToTarget": True,
            "paintStroke": {
                "color": "#e63946",
                "radiusSourcePx": 6,
                "regionUV": [.15, .15, .85, .85],
            }
        }
        self.shot["requirePhysicalContacts"] = True
        self.shot["contactConstraints"] = [self.rule]

    def tearDown(self):
        self.tmp.cleanup()

    def prepared(self):
        return check(self.config, self.registry, self.root)

    def pixel_on_wall(self, prepared, view, f, uv=(.5, .5)):
        comp = prepared["scenes"][0]["compositions"][view]
        wall = next(x for x in comp["elements"] if x["assetId"] == "desk")
        p, _ = _screen_xy(wall, uv, f, comp["camera"], SIZES[view],
                          prepared["artwork"]["desk"].size, interpolate)
        return tuple(round(x) for x in p)

    def test_before_roller_vs_after_roller_real_render_pixels_both_formats(self):
        prepared = self.prepared()
        self.assertEqual(prepared["paintStrokesRendered"], 1)
        self.assertEqual(prepared["contactLocksRendered"], 2)
        self.assertEqual(prepared["contactConstraintsChecked"], 1)
        for portrait, view in ((False, "landscape"), (True, "portrait")):
            with self.subTest(view=view):
                scene = DirectedScene(self.config, self.registry, self.root,
                                      portrait=portrait, prepared=prepared)
                before = scene.frame(0, self.actor)
                after = scene.frame(479, self.actor)
                pos0 = self.pixel_on_wall(prepared, view, 0, (.5, .8))
                pos1 = self.pixel_on_wall(prepared, view, 479)
                self.assertEqual(before.size, SIZES[view])
                self.assertEqual(after.size, SIZES[view])
                self.assertEqual(before.getpixel(pos0), WALL)
                self.assertEqual(after.getpixel(pos1), PAINT)
                trail = prepared["scenes"][0]["paintTracks"][view]["desk"]
                self.assertGreater(len(set(trail.points)), 2)

    def test_random_frame_seek_is_deterministic_and_future_paint_does_not_leak(self):
        prepared = self.prepared()
        scene = DirectedScene(self.config, self.registry, self.root, prepared=prepared)
        late = scene.frame(479, self.actor)
        early = scene.frame(0, self.actor)
        mid = scene.frame(300, self.actor)
        late_again = scene.frame(479, self.actor)
        site = self.pixel_on_wall(prepared, "landscape", 479)
        self.assertEqual(early.getpixel(self.pixel_on_wall(prepared, "landscape", 0, (.5, .8))), WALL)
        self.assertEqual(late.getpixel(site), PAINT)
        self.assertEqual(late_again.getpixel(site), PAINT)
        self.assertEqual(hashlib.sha256(late.tobytes()).digest(),
                         hashlib.sha256(late_again.tobytes()).digest())
        self.assertNotEqual(hashlib.sha256(mid.tobytes()).digest(),
                            hashlib.sha256(early.tobytes()).digest())

    def test_author_png_and_keyframes_never_modified(self):
        source_file = self.root / "desk.png"
        before_png = source_file.read_bytes()
        before_keys = json.dumps(self.config, sort_keys=True)
        data = self.prepared()
        scene = DirectedScene(self.config, self.registry, self.root, prepared=data)
        scene.frame(479, self.actor)
        self.assertEqual(source_file.read_bytes(), before_png)
        self.assertEqual(json.dumps(self.config, sort_keys=True), before_keys)
        self.assertFalse(data["creativeApproved"])

    def test_paint_sticks_to_moving_and_rotating_wall(self):
        for view in SIZES:
            comp = self.shot["compositions"][view]
            wall = next(x for x in comp["elements"] if x["assetId"] == "desk")
            wall["keys"] = [key(0, .5, .5, scale=.7, rotation=0.),
                            key(480, .54, .5, scale=.7, rotation=10.)]
            # Author the roller's release near the moved wall, so a real
            # contact lock cannot hide a teleport when the brush lifts off.
            tool = next(x for x in comp["elements"] if x["assetId"] == "globe")
            tool["keys"][3]["x"] = .535
            tool["keys"][4]["x"] = .54
        prepared = self.prepared()
        for portrait, view in ((False, "landscape"), (True, "portrait")):
            scene = DirectedScene(self.config, self.registry, self.root,
                                  portrait=portrait, prepared=prepared)
            rgb = scene.frame(479, self.actor)
            pos = self.pixel_on_wall(prepared, view, 479)
            self.assertEqual(rgb.getpixel(pos), PAINT)

    def test_paint_clips_at_source_alpha_and_author_region(self):
        self.rule["paintStroke"]["radiusSourcePx"] = 24
        self.rule["paintStroke"]["regionUV"] = [0, 0, 1, 1]
        prepared = self.prepared()
        paint = prepared["scenes"][0]["paintTracks"]["landscape"]["desk"]
        image = paint.source_at(479)
        original = prepared["artwork"]["desk"]
        self.assertEqual(image.getpixel((0, 0)), original.getpixel((0, 0)))
        self.assertEqual(image.getpixel((139, 139)), original.getpixel((139, 139)))
        self.assertEqual(image.getpixel((70, 70))[:3], PAINT)

    def test_undirected_legacy_scene_does_not_gain_paint(self):
        self.rule.pop("paintStroke")
        clean = self.prepared()
        self.assertEqual(clean["paintStrokesRendered"], 0)
        self.assertEqual(clean["scenes"][0]["paintEvidence"], {})
        scene = DirectedScene(self.config, self.registry, self.root, prepared=clean)
        frame = scene.frame(479, self.actor)
        site = self.pixel_on_wall(clean, "landscape", 479)
        self.assertEqual(frame.getpixel(site), WALL)

    def test_paint_without_contact_lock_refused(self):
        self.rule["lockToolToTarget"] = False
        with self.assertRaisesRegex(ValueError, "detached|requires locked actual"):
            self.prepared()

    def test_region_must_contain_authorized_tool_path(self):
        self.rule["paintStroke"]["regionUV"] = [.8, .8, 1., 1.]
        with self.assertRaisesRegex(ValueError, "outside the authored painted-wall region"):
            self.prepared()

    def test_color_and_brush_validation(self):
        for invalid in ("#FAKE99", "white", 7, "#abc"):
            with self.subTest(invalid=invalid):
                self.rule["paintStroke"]["color"] = invalid
                with self.assertRaisesRegex(ValueError, "paint color|invalid paint color|color must"):
                    self.prepared()
        self.rule["paintStroke"]["color"] = "#e63946"
        for invalid in (0, 25, True, 1.2):
            with self.subTest(invalid=invalid):
                self.rule["paintStroke"]["radiusSourcePx"] = invalid
                with self.assertRaisesRegex(ValueError, "radiusSourcePx"):
                    self.prepared()

    def test_cannot_paint_invisible_png_padding(self):
        self.rule["target"]["segment"] = [[.01, .1], [.01, .8]]
        with self.assertRaisesRegex(ValueError, "transparent artwork|transparent source-wall|no visible artwork"):
            self.prepared()

    def test_target_layer_must_render_before_roller(self):
        for view in SIZES:
            comp = self.shot["compositions"][view]
            comp["elements"] = [comp["elements"][2], *comp["elements"][:2]]
        with self.assertRaisesRegex(ValueError, "must render behind"):
            self.prepared()

    def test_no_progressive_paint_in_stationary_roller_shot(self):
        for view in SIZES:
            roller = self.shot["compositions"][view]["elements"][-1]
            roller["keys"] = [key(0,.5,.5,scale=.5), key(60,.5,.5,scale=.5), key(240,.6,.5,scale=.5), key(420,.5,.5,scale=.5), key(480,.5,.5,scale=.5)]
        with self.assertRaisesRegex(ValueError, "no progressive stroke"):
            self.prepared()

    def test_never_accept_duplicate_paint_on_same_wall(self):
        second = dict(self.rule, startFrame=420, endFrameExclusive=425)
        self.shot["contactConstraints"].append(second)
        with self.assertRaisesRegex(ValueError, "Multiple independent paint strokes|abrupt"):
            self.prepared()


if __name__ == "__main__":
    unittest.main()
