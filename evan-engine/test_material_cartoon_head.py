"""Material coverage/regression checks; not lip-sync or art acceptance."""
import unittest
import numpy as np
from material_cartoon_head import MaterialCartoonHead
from rounded_cartoon_head import RoundedCartoonHead

class MaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=RoundedCartoonHead();cls.new=MaterialCartoonHead()
    def test_shared_opaque_material_does_not_expose_skin(self):
        face=np.array([[[240.,170.,90.,255.]]]);ink=np.array([[[22.,10.,8.,255.]]]);zero=np.zeros_like(ink)
        for f in [.1,.25,.5,.75,.9]:
            w=np.zeros(9);w[2]=1-f;w[7]=f
            out=self.new.composite_oral(face,ink,zero,zero,ink,zero,20,w)
            np.testing.assert_allclose(out,ink,atol=1e-5)
    def test_pure_poses_remain_exact(self):
        for w in np.eye(9):np.testing.assert_array_equal(self.old.weights(w),self.new.weights(w))
    def test_non_contact_blends_remain_exact(self):
        for i in [2,5,6,8]:
            w=np.eye(9)[0]*.4+np.eye(9)[i]*.6
            np.testing.assert_array_equal(self.old.weights(w),self.new.weights(w))
    def test_contact_change_confined_to_mouth(self):
        w=np.zeros(9);w[0]=.027;w[2]=.522;w[7]=.451
        a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));mask=np.ones(a.shape[:2],bool);mask[300:385,180:295]=False
        np.testing.assert_array_equal(a[mask],b[mask]);self.assertGreater(np.count_nonzero(a!=b),0)
