"""Source-art physical contact regressions for directed 60fps scenes.

The imported fixture builds real local PNGs and independent portrait/landscape
compositions. No private Evan audio, renderer output, or fabricated human approval.
"""
import unittest
from directed_scene import check
from test_directed_scene import DirectedSceneTests, fixture  # reuse real fixture geometry
from pathlib import Path
import tempfile


class DirectedContactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan, self.registry = fixture(self.root)
        self.shot = self.plan["shots"][0]
        # Both source assets use the same physical screen center throughout the
        # contact interval. A 10-degree rotation supplies real prop motion.
        for view in ("landscape", "portrait"):
            comp = self.shot["compositions"][view]
            for asset_id in ("desk", "globe"):
                layer = next(e for e in comp["elements"] if e["assetId"] == asset_id)
                for k in layer["keys"]:
                    k["x"] = .5
                    k["y"] = .5
                    k["rotation"] = 0 if asset_id == "desk" else (10 if k["frame"] else 0)
        self.contact = {
            "startFrame": 120, "endFrameExclusive": 180,
            "tool": {"assetId": "globe", "uv": [.5, .5]},
            "target": {"assetId": "desk", "uv": [.5, .5]},
            "maxGapPx": 3
        }
        self.shot["contactConstraints"] = [self.contact]

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_prop_contact_checked_every_frame_both_orientations(self):
        result = check(self.plan, self.registry, self.root)
        self.assertEqual(result["contactConstraintsChecked"], 1)
        report = result["scenes"][0]["contactEvidence"]
        self.assertFalse(report["artisticApproval"])
        self.assertFalse(report["actorHandRigValidated"])
        self.assertEqual(report["details"][0]["views"]["portrait"]["framesChecked"], 60)
        self.assertEqual(report["details"][0]["views"]["landscape"]["framesChecked"], 60)
        self.assertLessEqual(report["details"][0]["views"]["portrait"]["maximumMeasuredGapPx"], 3)

    def test_detached_roller_equivalent_fails_before_any_frame_render(self):
        self.shot["compositions"]["landscape"]["elements"][-1]["keys"][-1]["x"] = .9
        with self.assertRaisesRegex(ValueError, "detached landscape prop at frame"):
            check(self.plan, self.registry, self.root)

    def test_independent_portrait_placement_must_pass_itself(self):
        self.shot["compositions"]["portrait"]["elements"][-1]["keys"][-1]["x"] = .8
        with self.assertRaisesRegex(ValueError, "detached portrait prop at frame"):
            check(self.plan, self.registry, self.root)

    def test_contact_to_wall_segment_uses_distance_to_edge(self):
        self.contact["target"] = {"assetId": "desk", "segment": [[.5, .05], [.5, .95]]}
        self.assertEqual(check(self.plan, self.registry, self.root)["contactConstraintsChecked"], 1)

    def test_bad_segment_is_rejected(self):
        self.contact["target"] = {"assetId": "desk", "segment": [[.5, .5], [.5, .5]]}
        with self.assertRaisesRegex(ValueError, "zero-length segment"):
            check(self.plan, self.registry, self.root)

    def test_nonfinite_or_missing_anchor_rejected(self):
        self.contact["tool"]["uv"] = [float("nan"), .5]
        with self.assertRaisesRegex(ValueError, "normalized"):
            check(self.plan, self.registry, self.root)

    def test_unsupported_approximate_actor_hand_is_not_certified(self):
        self.contact["tool"]["assetId"] = "original-evan-rig"
        with self.assertRaisesRegex(ValueError, "actor rig anchors are not supported"):
            check(self.plan, self.registry, self.root)

    def test_unregistered_target_is_rejected(self):
        self.contact["target"]["assetId"] = "invented-wall"
        with self.assertRaisesRegex(ValueError, "registered"):
            check(self.plan, self.registry, self.root)

    def test_fully_invisible_target_is_rejected(self):
        layer = self.shot["compositions"]["portrait"]["elements"][0]
        for k in layer["keys"]:
            k["opacity"] = 0
        with self.assertRaisesRegex(ValueError, "invisible contact"):
            check(self.plan, self.registry, self.root)

    def test_contact_outside_scene_interval_rejected(self):
        self.contact["endFrameExclusive"] = 481
        with self.assertRaisesRegex(ValueError, "invalid contact frame interval"):
            check(self.plan, self.registry, self.root)

    def test_overly_permissive_contact_not_allowed(self):
        self.contact["maxGapPx"] = 500
        with self.assertRaisesRegex(ValueError, "maxGapPx"):
            check(self.plan, self.registry, self.root)

    def test_deliberately_required_contact_is_not_a_free_pass(self):
        self.shot["requirePhysicalContacts"] = True
        self.shot["contactConstraints"] = []
        with self.assertRaisesRegex(ValueError, "Required physical prop contact"):
            check(self.plan, self.registry, self.root)

    def test_legacy_scene_without_contact_fields_is_unchanged(self):
        self.shot.pop("contactConstraints")
        result = check(self.plan, self.registry, self.root)
        self.assertEqual(result["contactConstraintsChecked"], 0)
        self.assertEqual(result["totalFrames"], 2400)

    def test_contact_points_follow_camera_without_false_detach(self):
        # Camera movement applies equally to both original-art layers.
        for view in ("portrait", "landscape"):
            c = self.shot["compositions"][view]["camera"]
            c[0]["panX"] = -.1
            c[1]["panX"] = .1
        self.assertEqual(check(self.plan, self.registry, self.root)["contactConstraintsChecked"], 1)

    def test_duplicated_contact_layer_is_ambiguous(self):
        comp = self.shot["compositions"]["landscape"]
        comp["elements"].append(dict(comp["elements"][0]))
        with self.assertRaisesRegex(ValueError, "exactly one layer"):
            check(self.plan, self.registry, self.root)


if __name__ == "__main__":
    unittest.main()
