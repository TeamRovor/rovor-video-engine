"""Root/occlusion/containment safeguards, not anatomical or sync acceptance."""
import unittest
import numpy as np
from lingual_cartoon_head import LingualCartoonHead,tongue_matrix,tongue_lift
from material_cartoon_head import MaterialCartoonHead

class LingualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=MaterialCartoonHead();cls.new=LingualCartoonHead()
    def test_root_stays_fixed_while_tip_rises(self):
        tips=[]
        for lift in np.linspace(0,1,11):
            m=tongue_matrix(lift)
            np.testing.assert_allclose(m@[237,354,1],[237,354],atol=2e-5)
            tips.append((m@[237,322,1])[1])
        self.assertTrue(np.all(np.diff(tips)<0))
    def test_existing_l_identity_is_used(self):
        w=np.zeros(9);w[2]=.3;w[8]=.7
        self.assertAlmostEqual(tongue_lift(w),.7)
        self.assertAlmostEqual(tongue_lift(w*10),.7)
    def test_upper_teeth_occlude_blade(self):
        zero=np.zeros((1,1,4),np.float32)
        cavity=np.array([[[30.,10.,10.,255.]]]);tongue=np.array([[[180.,70.,70.,255.]]]);teeth=np.array([[[240.,230.,200.,255.]]])
        out=self.new.composite_oral(zero,cavity,teeth,tongue,zero,zero,30,np.eye(9)[8])
        np.testing.assert_allclose(out,teeth)
    def test_closed_and_fv_poses_unchanged(self):
        for i in [0,1,7]:
            np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_geometry_and_nonoral_pixels_unchanged(self):
        mask=np.ones((512,512),bool);mask[300:385,180:295]=False
        changed=False
        for w in list(np.eye(9))+[np.eye(9)[2]*.4+np.eye(9)[8]*.6,np.eye(9)[2]*.5+np.eye(9)[7]*.5]:
            np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w))
            np.testing.assert_array_equal(a[mask],b[mask]);changed|=np.any(a!=b)
        self.assertTrue(changed)
