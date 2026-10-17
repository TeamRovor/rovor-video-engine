import unittest
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_hand import split_hand,transformed_hand
from cartoon_gesture_body import CartoonGestureBody,pointing_acting
from painted_character import arm_transforms,skin_vertices

class CartoonHandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.body=CartoonGestureBody()
    def test_extended_gesture_has_no_arm_foldovers(self):
        for t in np.arange(231)/48:
            for n,arm in self.body.arms.items():
                v=skin_vertices(arm.vertices,arm.geometry,pointing_acting(float(t))[n]);tri=v[np.asarray(arm.triangles)];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),1)
    def test_wrist_drawings_follow_parent_joint(self):
        arm=self.body.arms['right'];p=np.r_[arm.geometry['wrist'],1]
        for t in np.arange(231)/48:
            u,f,h=arm_transforms(arm.geometry,pointing_acting(float(t))['right']);np.testing.assert_allclose(f@p,h@p,atol=.001)
    def test_split_removes_original_fingers_from_forearm(self):
        arm=self.body.arms['right'];source=Image.open(ROOT/'body-rig/arm-right.png').convert('RGBA');fore,hand=split_hand(source,arm.geometry)
        self.assertEqual(np.asarray(fore)[820:,:,3].max(),0)
        self.assertGreater(np.asarray(hand)[820:,:,3].max(),200)
    def test_rigid_hand_does_not_change_with_elbow_mesh(self):
        # The hand is resampled by a single bone transform, never per-finger mesh.
        hand=self.body.hands['right']['point'];g=self.body.arms['right'].geometry
        out=transformed_hand(hand,g,[0,0,0],canvas=(1024,1536),pad=0)
        a=np.asarray(hand);b=np.asarray(out);mask=a[:,:,3]>250
        self.assertLess(float(np.abs(a.astype(float)[mask]-b.astype(float)[mask]).mean()),1)
if __name__=='__main__':unittest.main()
