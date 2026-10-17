"""Avoid calling a talking head a visually varied cartoon."""
import unittest
import numpy as np
from visual_dynamics_audit import summarize

class MotionAuditTests(unittest.TestCase):
    def test_mouth_hand_only_is_rejected(self):
        frames=[np.zeros((180,320,3),np.uint8) for _ in range(22)]
        for i,frame in enumerate(frames):frame[50:75,20:30]=(i*7)%256
        report=summarize(frames,list(range(22)),22)
        self.assertEqual(report['status'],'VISUAL_REVIEW_REQUIRED')
        self.assertFalse(report['publicationApproved'])

    def test_real_scene_composition_changes_are_detected(self):
        frames=[]
        for i in range(23):
            frame=np.zeros((180,320,3),np.uint8)
            frame[:,160:]=((i//6)*63)%256
            frames.append(frame)
        report=summarize(frames,list(range(23)),22)
        self.assertEqual(report['status'],'STRUCTURAL_MOTION_PRESENT')
        self.assertFalse(report['isEntertainmentCertified'])

    def test_inconsistent_frame_shape_rejected(self):
        with self.assertRaises(ValueError):
            summarize([np.zeros((12,12,3)),np.zeros((10,10,3))],[0,1],2)

if __name__=='__main__':unittest.main()
