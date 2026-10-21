"""Non-Moho native 60fps actual frame composition with physical wall contact.

Source-free original-art PNG fixtures; both 1080p60 formats rendered using
the project's existing DirectedScene.frame, never using Moho or generic art.
"""
import tempfile
import unittest
from pathlib import Path

from directed_scene import DirectedScene, check, interpolate, SIZES
from directed_contact import _screen_xy
from test_directed_scene import fixture, key, camera
from PIL import Image


class LockedAnimationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config, self.registry = fixture(self.root)
        self.actor = Image.new("RGBA", (280, 360), (0, 0, 0, 0))
        self.shot = self.config["shots"][0]
        for view in ("landscape", "portrait"):
            comp = self.shot["compositions"][view]
            desk = next(e for e in comp["elements"] if e["assetId"] == "desk")
            tool = next(e for e in comp["elements"] if e["assetId"] == "globe")
            desk["keys"] = [key(0, .5, .5, scale=.7),
                            key(480, .5, .5, scale=.7)]
            # Authored motion moves the prop 230px off the wall in landscape.
            # Keep the gesture along Y; locking must adjust only x as needed.
            tool["keys"] = [
                key(0, .5, .49, scale=.5),
                key(240, .62, .5, scale=.5),
                key(480, .5, .51, scale=.5)]
        self.contact = {
            "startFrame": 0, "endFrameExclusive": 480,
            "tool": {"assetId": "globe", "uv": [.5, .5]},
            "target": {"assetId": "desk",
                       "segment": [[.5, .25], [.5, .75]]},
            "maxGapPx": 2,
            "maxCorrectionPx": 255,
            "lockToolToTarget": True,
        }
        self.shot["requirePhysicalContacts"] = True
        self.shot["contactConstraints"] = [self.contact]

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self):
        return check(self.config, self.registry, self.root)

    def test_detached_original_art_is_physically_locked_in_both_real_frames(self):
        verified = self.prepare()
        self.assertEqual(verified["contactConstraintsChecked"], 1)
        self.assertEqual(verified["contactLocksRendered"], 2)
        for portrait, view in ((False, "landscape"), (True, "portrait")):
            with self.subTest(view=view):
                evidence = verified["scenes"][0]["contactEvidence"]["details"][0]["views"][view]
                self.assertEqual(evidence["framesChecked"], 480)
                self.assertLessEqual(evidence["maximumMeasuredGapPx"], 2)
                scene = DirectedScene(self.config, self.registry, self.root,
                                      portrait=portrait, prepared=verified)
                frame = scene.frame(240, self.actor)
                self.assertEqual(frame.size, SIZES[view])
                view_data = verified["scenes"][0]["compositions"][view]
                desk = next(e for e in view_data["elements"] if e["assetId"] == "desk")
                target, _ = _screen_xy(desk, (.5, .5), 240, view_data["camera"],
                                       SIZES[view], verified["artwork"]["desk"].size,
                                       interpolate)
                center = tuple(round(c) for c in target)
                pixel = frame.getpixel(center)
                self.assertEqual(pixel, (60, 155, 161))  # real drawn globe plate

    def test_same_narrative_unlocked_has_visible_wrong_pixels(self):
        self.contact["lockToolToTarget"] = False
        with self.assertRaisesRegex(ValueError, "detached"):
            self.prepare()
        self.shot.pop("contactConstraints")
        self.shot.pop("requirePhysicalContacts")
        verified = self.prepare()
        frame = DirectedScene(self.config, self.registry, self.root,
                              prepared=verified).frame(240, self.actor)
        view_data = verified["scenes"][0]["compositions"]["landscape"]
        desk = next(e for e in view_data["elements"] if e["assetId"] == "desk")
        target, _ = _screen_xy(desk, (.5, .5), 240, view_data["camera"],
                               SIZES["landscape"], verified["artwork"]["desk"].size,
                               interpolate)
        self.assertEqual(frame.getpixel(tuple(round(c) for c in target)),
                         (134, 107, 82))  # desk, globe visibly detached

    def test_author_original_tracks_unmodified(self):
        before = [list(e["keys"]) for e in self.shot["compositions"]["portrait"]["elements"]]
        ready = self.prepare()
        self.assertEqual(before, [list(e["keys"]) for e in self.shot["compositions"]["portrait"]["elements"]])
        after = ready["scenes"][0]["compositions"]["portrait"]["elements"][-1]["keys"]
        self.assertGreater(len(after), 400)
        self.assertEqual(after[0][0], 0)
        self.assertEqual(after[-1][0], 480)
        self.assertFalse(ready["creativeApproved"])

    def test_portrait_and_landscape_are_truly_independent(self):
        portrait = self.shot["compositions"]["portrait"]["elements"][-1]
        portrait["keys"][1]["x"] = .73  # exceeds authorized correction in portrait
        with self.assertRaisesRegex(ValueError, "too far from target"):
            self.prepare()
        portrait["keys"][1]["x"] = .62
        self.assertEqual(self.prepare()["contactLocksRendered"], 2)

    def test_reject_completely_invisible_contact_edge(self):
        self.contact["target"]["segment"] = [[.01, .25], [.01, .75]]
        with self.assertRaisesRegex(ValueError, "target edge has no visible artwork"):
            self.prepare()

    def test_reject_tool_anchor_on_png_transparent_padding(self):
        self.contact["tool"]["uv"] = [.01, .01]
        with self.assertRaisesRegex(ValueError, "Transparent tool contact anchor"):
            self.prepare()

    def test_wrong_artistic_camera_scene_requires_no_auto_warp(self):
        for view in ("landscape", "portrait"):
            tool = self.shot["compositions"][view]["elements"][-1]
            tool["keys"][1]["x"] = .91
        with self.assertRaisesRegex(ValueError, "too far from target"):
            self.prepare()

    def test_actor_hand_cannot_be_pretended_as_real_prop(self):
        self.contact["tool"]["assetId"] = "original-evan-rig"
        with self.assertRaisesRegex(ValueError, "not actor hand"):
            self.prepare()

    def test_duplicate_ambiguous_prop_is_not_silently_attached(self):
        comp = self.shot["compositions"]["landscape"]
        comp["elements"].append(dict(comp["elements"][-1]))
        with self.assertRaisesRegex(ValueError, "Ambiguous tool"):
            self.prepare()

    def test_strict_lock_fields(self):
        self.contact["lockToolToTarget"] = "true"
        with self.assertRaisesRegex(ValueError, "must be boolean"):
            self.prepare()
        self.contact["lockToolToTarget"] = True
        self.contact["maxCorrectionPx"] = 500
        with self.assertRaisesRegex(ValueError, "maxCorrectionPx"):
            self.prepare()

    def test_reject_unplanned_entrance_teleport(self):
        self.contact["startFrame"] = 240
        self.contact["endFrameExclusive"] = 480
        with self.assertRaisesRegex(ValueError, "abrupt lock entrance"):
            self.prepare()

    def test_reject_unplanned_release_teleport(self):
        self.contact["endFrameExclusive"] = 241
        with self.assertRaisesRegex(ValueError, "abrupt lock release"):
            self.prepare()

    def test_overlapping_tool_locks_cannot_fight(self):
        other = dict(self.contact, startFrame=120, endFrameExclusive=360)
        self.shot["contactConstraints"].append(other)
        with self.assertRaisesRegex(ValueError, "Overlapping contact locks"):
            self.prepare()

    def test_legacy_unlocked_scene_no_behavior_change(self):
        self.shot.pop("contactConstraints")
        self.shot.pop("requirePhysicalContacts")
        result = self.prepare()
        self.assertEqual(result["contactConstraintsChecked"], 0)
        self.assertEqual(result["contactLocksRendered"], 0)
        self.assertEqual(len(result["scenes"][0]["compositions"]["landscape"]["elements"][-1]["keys"]), 3)
        self.assertEqual(DirectedScene(self.config, self.registry, self.root, prepared=result).frame(240, self.actor).size, SIZES["landscape"])

    def test_camera_translation_does_not_detach_tool(self):
        for view in ("portrait", "landscape"):
            cam = self.shot["compositions"][view]["camera"]
            cam[0]["panX"], cam[-1]["panX"] = -.25, .25
        self.assertEqual(self.prepare()["contactConstraintsChecked"], 1)


if __name__ == "__main__":
    unittest.main()
