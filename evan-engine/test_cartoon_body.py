"""Geometric safeguards for the opt-in body study; no visual quality claim."""
import unittest
import numpy as np
from cartoon_body import CartoonBody,acting
from painted_character import arm_transforms,skin_vertices

class CartoonBodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.body=CartoonBody()
    def test_no_foldovers_in_authored_shot(self):
        for t in np.arange(231)/48:
            for name,arm in self.body.arms.items():
                v=skin_vertices(arm.vertices,arm.geometry,acting(float(t))[name]);tri=v[np.asarray(arm.triangles)]
                a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),1)
                self.assertGreater(float(v[:,0].min()+220),0)
                self.assertLess(float(v[:,0].max()+220),1464)
    def test_child_joints_remain_attached(self):
        for arm in self.body.arms.values():
            for angles in [(6,18,4),(-6,-18,-4)]:
                u,f,h=arm_transforms(arm.geometry,angles)
                elbow=np.r_[arm.geometry['elbow'],1];wrist=np.r_[arm.geometry['wrist'],1]
                np.testing.assert_allclose(u@elbow,f@elbow,atol=.001)
                np.testing.assert_allclose(f@wrist,h@wrist,atol=.001)
    def test_left_right_controls_are_independent(self):
        left=self.body.arms['left'];before=skin_vertices(left.vertices,left.geometry,(0,0,0));after=skin_vertices(left.vertices,left.geometry,(6,18,4))
        self.assertGreater(float(np.max(abs(after-before))),20)
        right=self.body.arms['right'];rest=skin_vertices(right.vertices,right.geometry,(0,0,0))
        np.testing.assert_allclose(rest,right.vertices,atol=.001)
if __name__=='__main__':unittest.main()
