"""Real original Evan alpha QA immediately before standalone FFmpeg stream.

Actual original cartoon body art is loaded and rasterized from this repo;
source-free synthetic variants deliberately erase the wrist and must fail.
"""
import unittest
from PIL import Image, ImageDraw
from cartoon_body import CartoonBody
from grip_raster_qa import check_frame, _sample_coverage
from right_hand_grip import _inside_canvas_wrist, wrist_xy
from test_right_hand_grip import RealWristGripTests


class RasterGripQATests(unittest.TestCase):
    def setUp(self):
        self.test = RealWristGripTests("test_real_source_joint_original_manifest_binding_and_motion")
        self.test.setUp()
        self.addCleanup(self.test.doCleanups)
        self.prepared = self.test.prepared()
        self.shot = self.prepared["scenes"][0]
        self.body = CartoonBody()
        self.sample_frame = 150
        self.authored = self.test.performance.at_frame(self.sample_frame)
        self.solved = dict(self.authored,
                           right=self.shot["gripControls"][self.sample_frame])
        self.speech = {"alignment":{"status":"acoustic"},
                       "phonemes":[],"fallbackCues":[],
                       "audio":{"energy":[0.],"step":.1}}
        self.actual_actor = self.body.render(
            self.sample_frame / 60, self.speech, self.solved)

    def check(self, figure=None, frame=None, shot=None, controls=None):
        return check_frame(self.actual_actor if figure is None else figure,
                           self.sample_frame if frame is None else frame,
                           self.shot if shot is None else shot,
                           self.solved if controls is None else controls,
                           self.test.meta, self.test.hand)

    def test_real_original_painted_evan_hand_wrist_raster_is_present(self):
        result=self.check()
        self.assertTrue(result["wristArtworkPresent"])
        self.assertGreaterEqual(result["opaqueSamples"],6)
        self.assertFalse(result["fingerCurlVerified"])
        self.assertFalse(result["studioApproved"])

    def test_real_original_wrist_pixel_erasure_is_rejected(self):
        wrist=_inside_canvas_wrist(
            wrist_xy(self.test.meta,self.test.hand,self.solved["right"]),
            self.solved["body_roll"])
        missing=self.actual_actor.copy()
        ImageDraw.Draw(missing).ellipse((wrist[0]-18,wrist[1]-18,
                                         wrist[0]+18,wrist[1]+18),
                                        fill=(0,0,0,0))
        with self.assertRaisesRegex(ValueError,"visually missing"):
            self.check(figure=missing)

    def test_completely_missing_actor_is_rejected_before_encode(self):
        with self.assertRaisesRegex(ValueError,"visually missing"):
            self.check(figure=Image.new("RGBA",(1464,1536)))

    def test_unadjusted_actor_controls_fail_even_if_source_alpha_exists(self):
        with self.assertRaisesRegex(ValueError,"Cached or uncorrected"):
            self.check(controls=self.authored)

    def test_legacy_or_ungripped_frame_does_not_introduce_false_rejection(self):
        self.assertIsNone(self.check(frame=0))
        no_grips=dict(self.shot,gripControls={})
        self.assertIsNone(self.check(shot=no_grips))

    def test_rejects_rgb_actor_or_wrong_cached_body_dimensions(self):
        with self.assertRaisesRegex(ValueError,"actual RGBA"):
            self.check(figure=self.actual_actor.convert("RGB"))
        with self.assertRaisesRegex(ValueError,"actual RGBA"):
            self.check(figure=Image.new("RGBA",(280,360)))

    def test_source_alpha_coverage_boundary_is_a_minimal_gate_not_art_approval(self):
        result=self.check()
        self.assertGreater(result["totalSamples"],result["opaqueSamples"]-1)
        self.assertFalse(result["studioApproved"])

    def test_switching_to_pointing_pose_does_not_fake_a_grip(self):
        wrong=dict(self.solved, right_hand="point")
        with self.assertRaisesRegex(ValueError,"relaxed-right"):
            self.check(controls=wrong)

    def test_unsafe_missing_original_hand_manifest_is_blocked(self):
        altered=dict(self.test.hand)
        altered.pop("relaxed-right")
        with self.assertRaisesRegex(ValueError,"authentic source"):
            check_frame(self.actual_actor,self.sample_frame,self.shot,
                        self.solved,self.test.meta,altered)


if __name__=="__main__":
    unittest.main()
