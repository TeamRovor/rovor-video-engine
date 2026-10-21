"""Actual source-painted Evan hand foreground pixels over a held prop.

Not a synthetic stick hand: this test uses existing original CartoonBody
and the registered relaxed-right WristPlate, with the calibrated FK right
wrist shared between portrait and landscape.
"""
import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from cartoon_body import CartoonBody
from directed_scene import DirectedScene, check, SIZES, interpolate, ACTOR_ID
from directed_contact import _screen_xy
from directed_grip_occlusion import ForegroundHand, grip_foreground_rules
from right_hand_grip import wrist_xy, _inside_canvas_wrist, ACTOR_SIZE
from test_right_hand_grip import RealWristGripTests


class OriginalHandOverPropTests(unittest.TestCase):
    def setUp(self):
        self.src=RealWristGripTests("test_real_source_joint_original_manifest_binding_and_motion")
        self.src.setUp()
        self.addCleanup(self.src.doCleanups)
        self.prepared=self.src.prepared()
        self.shot=self.prepared["scenes"][0]
        self.body=CartoonBody()
        self.frame_number=150
        base=self.src.performance.at_frame(self.frame_number)
        self.controls=dict(base,right=self.shot["gripControls"][self.frame_number])
        self.speech={"alignment":{"status":"acoustic"},
                     "phonemes":[],"fallbackCues":[],
                     "audio":{"energy":[0.],"step":.1}}
        self.actual_body=self.body.render(self.frame_number/60,self.speech,self.controls)

    def grip_pixel(self,view,frame):
        scene=self.shot["compositions"][view]
        actor=next(k for k in scene["elements"] if k["assetId"]==ACTOR_ID)
        local=_inside_canvas_wrist(wrist_xy(
            self.src.meta,self.src.hand,self.shot["gripControls"][frame]),
            self.src.performance.at_frame(frame)["body_roll"])
        point,_=_screen_xy(actor,(local[0]/ACTOR_SIZE[0],local[1]/ACTOR_SIZE[1]),
                           frame,scene["camera"],SIZES[view],ACTOR_SIZE,interpolate)
        return (round(point[0]),round(point[1]))

    def test_real_registered_hand_is_drawn_above_roller_in_both_formats(self):
        for portrait,view in ((False,"landscape"),(True,"portrait")):
            with self.subTest(view=view):
                renderer=DirectedScene(self.src.scene,self.src.assets,self.src.root,
                                       portrait=portrait,prepared=self.prepared)
                covered=renderer.frame(self.frame_number,self.actual_body)
                spot=self.grip_pixel(view,self.frame_number)
                self.assertEqual(covered.size,SIZES[view])
                old=self.shot["gripForeground"]
                self.shot["gripForeground"]={}
                try:
                    obscured=renderer.frame(self.frame_number,self.actual_body)
                finally:
                    self.shot["gripForeground"]=old
                self.assertNotEqual(covered.getpixel(spot),obscured.getpixel(spot))
                self.assertNotEqual(ImageChops.difference(covered,obscured).getbbox(),None)
                self.assertFalse(self.shot["gripEvidence"]["artisticApproval"])

    def test_identical_registered_source_wrist_art_reused_between_viewports(self):
        layer=self.shot["gripHandRaster"]
        self.assertIsInstance(layer,ForegroundHand)
        angles=self.shot["gripControls"][self.frame_number]
        image1=layer.image_at(self.frame_number,angles,0.)
        image2=layer.image_at(self.frame_number,angles,0.)
        self.assertIs(image1,image2)
        self.assertEqual(image1.size,ACTOR_SIZE)
        self.assertIsNotNone(image1.getchannel("A").getbbox())

    def test_physical_grip_hand_stays_hidden_before_pickup_and_after_release(self):
        for portrait in (False,True):
            scene=DirectedScene(self.src.scene,self.src.assets,self.src.root,
                                portrait=portrait,prepared=self.prepared)
            for frame in (0,450):
                self.assertNotIn(frame,self.shot["gripForeground"])
                actor=self.body.render(frame/60,self.speech,self.src.performance.at_frame(frame))
                normal=scene.frame(frame,actor)
                self.assertEqual(normal.size,scene.size)

    def test_original_hand_artwork_and_manifest_bytes_remain_intact(self):
        path=Path(__file__).parent.parent/"evan-character/cartoon-v1/hand-source/relaxed-right-v1.png"
        first=hashlib.sha256(path.read_bytes()).hexdigest()
        image=self.shot["gripHandRaster"].image_at(
            self.frame_number,self.shot["gripControls"][self.frame_number],
            self.src.performance.at_frame(self.frame_number)["body_roll"])
        self.assertIsNotNone(image.getchannel("A").getbbox())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),first)
        self.assertFalse(self.src.hand["visualApproved"])

    def test_rejects_source_hand_filename_path_escape(self):
        modified=json.loads(json.dumps(self.src.hand))
        modified["relaxed-right"]["file"]="../unregistered.png"
        with self.assertRaisesRegex(ValueError,"safe registered PNG"):
            ForegroundHand(self.src.meta,modified)

    def test_no_grip_scenes_require_no_foreground_hand_art(self):
        shot=self.src.scene["shots"][0]
        shot.pop("handGripConstraints")
        prepared=check(self.src.scene,self.src.assets,self.src.root)
        self.assertEqual(prepared["scenes"][0]["gripForeground"],{})
        self.assertIsNone(prepared["scenes"][0]["gripHandRaster"])
        renderer=DirectedScene(self.src.scene,self.src.assets,self.src.root,prepared=prepared)
        frame=renderer.frame(150,self.actual_body)
        self.assertEqual(frame.size,SIZES["landscape"])

    def test_multiple_held_tools_same_right_hand_cannot_overlay(self):
        other=dict(self.src.grip,startFrame=100,endFrameExclusive=240)
        self.src.scene["shots"][0]["handGripConstraints"].append(other)
        with self.assertRaisesRegex(ValueError,"Overlapping grip"):
            self.src.prepared()

    def test_original_view_order_maintains_behind_foreground_physical_rule(self):
        # Source wall/background is below Evan, held prop above actor;
        # only the authentic hand overlay is above this one prop. The last
        # element must never be an artificially generated foreground hand.
        for view in SIZES:
            elements=self.shot["compositions"][view]["elements"]
            self.assertLess([a["assetId"] for a in elements].index(ACTOR_ID),
                            [a["assetId"] for a in elements].index("globe"))
            self.assertNotIn("new-generated-hand", [a["assetId"] for a in elements])


if __name__=="__main__":
    unittest.main()
