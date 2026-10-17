import unittest
import numpy as np
from review_motion_discontinuity import measure_frames

class MotionReviewTests(unittest.TestCase):
    def test_identifies_exact_timed_pose_jump(self):
        frames=np.zeros((5,3,4,3),dtype=np.uint8)
        frames[3:]=90
        result=measure_frames(frames,60,start=2.0)
        self.assertEqual(result['frames'],5)
        self.assertEqual(result['topJumps'][0]['timeSeconds'],2.05)
        self.assertEqual(result['topJumps'][0]['meanAbsRgb'],90.0)
        self.assertEqual(result['topJumps'][0]['fractionChannelsOverThreshold'],1)
        self.assertEqual(result['integratedMeanAbsRgb'],90.0)

    def test_rejects_bad_shapes(self):
        with self.assertRaises(ValueError):measure_frames(np.zeros((2,4,4),dtype=np.uint8))
        with self.assertRaises(ValueError):measure_frames(np.zeros((1,4,4,3),dtype=np.uint8))

if __name__=='__main__':unittest.main()
