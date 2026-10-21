"""Source-FK-linked right wrist contact, both 1080p60 original-art compositions.

Fixture actor image is schematic test RGBA ONLY. Coordinates and hand pose
are taken from checked-in original Evan body-rig and hand-source manifests.
No realistic grip plate or finger articulation is falsely certified.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from directed_scene import DirectedScene, check, interpolate, SIZES
from directed_contact import _screen_xy
from performance_tracks import EvanPerformance
from right_hand_grip import (_body_local_target, _inside_canvas_wrist,
                             wrist_xy, _distance)
from test_directed_scene import fixture, key


ROOT = Path(__file__).resolve().parents[1]
CHARACTER = ROOT / "evan-character" / "cartoon-v1"


class RealWristGripTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scene, self.assets = fixture(self.root)
        self.meta = json.loads((CHARACTER / "body-rig" / "manifest.json").read_text())
        self.hand = json.loads((CHARACTER / "hand-source" / "manifest.json").read_text())
        self.actor = Image.new("RGBA", (1464, 1536))
        self.performance = EvanPerformance({
            "schemaVersion": 1,
            "sourceRig": "original-evan-layered",
            "durationSec": 40,
            "channels": {
                "right.shoulder": [
                    {"frame": 0, "degrees": 0},
                    {"frame": 2400, "degrees": 0},
                ],
                "right.elbow": [
                    {"frame": 0, "degrees": 0},
                    {"frame": 2400, "degrees": 0},
                ],
            },
            "rightHandKeys": [{"frame": 0, "pose": "relaxed"}],
        })
        shot = self.scene["shots"][0]
        self.grip = {
            "startFrame": 60, "endFrameExclusive": 420,
            "toolAssetId": "globe", "toolHandleUV": [.5, .5],
            "hand": "relaxed-right", "maxGripGapPx": 4,
        }
        shot["handGripConstraints"] = [self.grip]
        # The actual hand cannot change between 16:9 and 9:16. Author
        # independent prop layout in each view from the SAME source-FK wrist
        # pose while respecting the source frame/camera and original actor.
        for view, size in SIZES.items():
            comp = shot["compositions"][view]
            actor = next(i for i in comp["elements"]
                         if i["assetId"] == "original-evan-rig")
            prop = next(i for i in comp["elements"] if i["assetId"] == "globe")
            def pos(frame, angles):
                wrist = wrist_xy(self.meta, self.hand, (*angles, 0))
                source = _inside_canvas_wrist(wrist, 0)
                actor_xy = actor["keys"][0]  # storyboard fixture uses original dict keys
                return actor_xy["x"] + (source[0] - 732) * actor_xy["scale"] / size[0], (
                    actor_xy["y"] + (source[1] - 768) * actor_xy["scale"] / size[1])
            a = pos(0, (-1., 0.))
            mid = pos(240, (3., -4.))
            end = pos(480, (0., 0.))
            prop["keys"] = [
                key(0, a[0], a[1], scale=.5, rotation=0),
                key(240, mid[0], mid[1], scale=.5, rotation=9),
                key(480, end[0], end[1], scale=.5, rotation=0),
            ]
        self.initial = json.dumps(self.scene, sort_keys=True)

    def prepared(self):
        return check(self.scene, self.assets, self.root,
                     performance=self.performance, rig_meta=self.meta, hand_meta=self.hand)

    def test_real_source_joint_original_manifest_binding_and_motion(self):
        ready = self.prepared()
        self.assertEqual(ready["wristGripsSolved"], 1)
        shot = ready["scenes"][0]
        self.assertEqual(len(shot["gripControls"]), 360)
        self.assertFalse(shot["gripEvidence"]["realGripFingersValidated"])
        moved = [angles for angles in shot["gripControls"].values()
                 if abs(angles[0]) > .08 or abs(angles[1]) > .08]
        self.assertGreater(len(moved), 30)
        self.assertEqual(json.dumps(self.scene, sort_keys=True), self.initial)
        self.assertFalse(ready["creativeApproved"])

    def test_both_formats_track_the_exact_same_wrist_to_tool_handle(self):
        ready = self.prepared()
        shot = ready["scenes"][0]
        for view, canvas in SIZES.items():
            comp = shot["compositions"][view]
            actor = next(i for i in comp["elements"] if i["assetId"] == "original-evan-rig")
            tool = next(i for i in comp["elements"] if i["assetId"] == "globe")
            scene = DirectedScene(self.scene, self.assets, self.root,
                                  portrait=view == "portrait", prepared=ready)
            for f in range(60, 420):
                angles = scene.grip_at(f, self.performance.at_frame(f))["right"]
                self.assertLessEqual(abs(angles[0]), 12)
                self.assertLessEqual(abs(angles[1]), 30)
                point = _inside_canvas_wrist(wrist_xy(self.meta, self.hand, angles), 0)
                projected, _ = _screen_xy(actor, (point[0]/1464, point[1]/1536),
                                           f, comp["camera"], canvas, (1464,1536), interpolate)
                handle, _ = _screen_xy(tool, (.5, .5), f, comp["camera"],
                                       canvas, ready["artwork"]["globe"].size, interpolate)
                self.assertLessEqual(_distance(projected, handle), 4)
            frame = scene.frame(120, self.actor)
            self.assertEqual(frame.size, canvas)

    def test_real_original_rig_arm_raster_changes_from_solved_joint_controls(self):
        # The source actor geometry is not a cartoon stick figure. Exercise
        # the actual CartoonBody arm/hand plates with the corrected FK values
        # and verify the source-painted arm pixels move, not just JSON keys.
        from cartoon_body import CartoonBody
        from PIL import ImageChops
        ready = self.prepared()
        body = CartoonBody()
        pose = self.performance.at_frame(150)
        solved = dict(pose, right=ready["scenes"][0]["gripControls"][150])
        # Silence-stage pronunciation uses the existing acoustic rest pose.
        # No synthetic audio is presented as real source transcription.
        speech = {"alignment": {"status": "acoustic"},
                  "phonemes": [], "fallbackCues": [],
                  "audio": {"energy": [0.], "step": .1}}
        baseline_arm = body.layers(2.5, speech, pose)["arm-right"]
        gripping_arm = body.layers(2.5, speech, solved)["arm-right"]
        self.assertEqual(baseline_arm.size, (1464, 1536))
        self.assertIsNotNone(ImageChops.difference(baseline_arm, gripping_arm).getbbox())

    def test_missing_rig_or_performance_refused_before_render(self):
        with self.assertRaisesRegex(ValueError, "original FK performance"):
            check(self.scene, self.assets, self.root)
        with self.assertRaisesRegex(ValueError, "original FK performance"):
            check(self.scene, self.assets, self.root,
                  performance=self.performance, rig_meta=self.meta)

    def test_unregistered_tool_grip_anchor_cannot_be_invisible(self):
        self.grip["toolHandleUV"] = [.01, .01]
        with self.assertRaisesRegex(ValueError, "opaque original art"):
            self.prepared()

    def test_incompatible_landscape_portrait_wrist_target_rejected(self):
        prop = next(i for i in self.scene["shots"][0]["compositions"]["portrait"]["elements"]
                    if i["assetId"] == "globe")
        prop["keys"][1]["x"] += .055
        with self.assertRaisesRegex(ValueError, "incompatible grip targets"):
            self.prepared()

    def test_tool_more_than_source_arms_can_reach_is_not_teleported(self):
        for view, canvas in SIZES.items():
            comp = self.scene["shots"][0]["compositions"][view]
            prop = next(i for i in comp["elements"] if i["assetId"] == "globe")
            actor = next(i for i in comp["elements"] if i["assetId"] == "original-evan-rig")
            # Move by the same *actor-source-space* distance in both views,
            # not the same stage UV (which would create conflicting targets).
            dx = 120 * actor["keys"][0]["scale"] / canvas[0]
            for k in prop["keys"]:
                k["x"] += dx
        with self.assertRaisesRegex(ValueError, "cannot reach tool handle"):
            self.prepared()

    def test_wrong_right_hand_pose_refused_without_fake_grip(self):
        self.performance = EvanPerformance({
            "schemaVersion":1,"sourceRig":"original-evan-layered","durationSec":40,
            "channels":{"right.shoulder":[{"frame":0,"degrees":0},{"frame":2400,"degrees":0}]},
            "rightHandKeys":[{"frame":0,"pose":"point"}]})
        with self.assertRaisesRegex(ValueError, "not relaxed"):
            self.prepared()

    def test_missing_calibrated_source_hand_plate_rejected(self):
        del self.hand["relaxed-right"]
        with self.assertRaisesRegex(ValueError, "Missing original relaxed-right"):
            self.prepared()

    def test_original_hand_wrist_geometry_controls_real_fk_position(self):
        before = wrist_xy(self.meta,self.hand,(0,0,0))
        altered=copy.deepcopy(self.hand)
        altered["relaxed-right"]["rigWrist"][0]+=4
        after=wrist_xy(self.meta,altered,(0,0,0))
        self.assertEqual(after[0]-before[0],4)

    def test_experimental_source_art_not_treated_as_approved_grip(self):
        report=self.prepared()["scenes"][0]["gripEvidence"]
        self.assertFalse(report["artisticApproval"])
        self.assertFalse(report["realGripFingersValidated"])
        self.assertFalse(report["details"][0]["humanHandGripVisuallyApproved"])

    def test_legacy_scene_still_valid_and_performance_controls_not_changed(self):
        self.scene["shots"][0].pop("handGripConstraints")
        result=check(self.scene,self.assets,self.root)
        self.assertEqual(result["wristGripsSolved"],0)
        obj=DirectedScene(self.scene,self.assets,self.root,prepared=result)
        original=self.performance.at_frame(100)
        self.assertEqual(obj.grip_at(100,original),original)

    def test_actor_must_render_beneath_tool_for_visible_handle_contact(self):
        c=self.scene["shots"][0]["compositions"]["portrait"]
        c["elements"]=[c["elements"][-1],*c["elements"][:-1]]
        with self.assertRaisesRegex(ValueError,"composite in front"):
            self.prepared()

    def test_releasing_roller_mid_gesture_cannot_snap_original_arm(self):
        self.grip["endFrameExclusive"] = 200
        with self.assertRaisesRegex(ValueError, "release snaps original arm"):
            self.prepared()

    def test_no_overlap_of_distinct_wrist_targets(self):
        clone=dict(self.grip,startFrame=100,endFrameExclusive=120)
        self.scene["shots"][0]["handGripConstraints"].append(clone)
        with self.assertRaisesRegex(ValueError, "Overlapping grip"):
            self.prepared()


if __name__ == "__main__":
    unittest.main()
