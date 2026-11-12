import unittest
import numpy as np
from sh_cartoon_review import sh_shape_weights, sh_corner_target

class SHShapeTests(unittest.TestCase):
    def test_bounded_shifted_contacts_rest_and_immutability(self):
        base=np.array([.1,.1,.2,.1,.1,.1,.1,.1,.1]);saved=base.copy()
        plan={'phonemes':[dict(phone='SH',start=1.,end=1.13)]}
        shifted={'phonemes':[dict(phone='SH',start=3.,end=3.13)]}
        for t in np.linspace(.9,1.2,145):
            w=sh_shape_weights(t,plan,base)
            self.assertAlmostEqual(w.sum(),1);self.assertTrue((w>=0).all())
            np.testing.assert_array_equal(w[[1,7]],base[[1,7]])
            np.testing.assert_allclose(w,sh_shape_weights(t+2,shifted,base),atol=1e-12)
            if t<=1 or t>=1.13:np.testing.assert_array_equal(w,base)
        np.testing.assert_array_equal(base,saved)
        np.testing.assert_array_equal(sh_shape_weights(1.06,plan,np.eye(9)[0]),np.eye(9)[0])
        self.assertGreater(sh_shape_weights(1.06,plan,base)[5],base[5])
    def test_invalid_inputs(self):
        for t,w in [(np.nan,np.eye(9)[2]),(1,np.zeros(9)),(1,np.ones(8)),(1,-np.ones(9))]:
            with self.assertRaises(ValueError):sh_shape_weights(t,{},w)
        with self.assertRaises(ValueError):sh_shape_weights(1,{'phonemes':[dict(phone='SH',start=2,end=1)]},np.eye(9)[2])

    def test_corner_width_y_anchors_contacts_and_rest(self):
        oral=np.column_stack([np.linspace(200,275,51),np.linspace(310,390,51)])
        plan={'phonemes':[dict(phone='SH',start=1.,end=1.13)]}
        for t in [0,1,1.13,2]:np.testing.assert_array_equal(sh_corner_target(t,plan,oral,0),oral)
        target=sh_corner_target(1.06,plan,oral,0)
        np.testing.assert_array_equal(target[:,1],oral[:,1]);np.testing.assert_array_equal(target[32:],oral[32:])
        self.assertAlmostEqual(abs(target[0,0]-target[8,0]),.75*abs(oral[0,0]-oral[8,0]))
        np.testing.assert_array_equal(sh_corner_target(1.06,plan,oral,1),oral)
        for v in [-1,2,np.nan]:
            with self.assertRaises(ValueError):sh_corner_target(1.06,plan,oral,v)

if __name__=='__main__':unittest.main()
