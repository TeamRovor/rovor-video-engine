"""Contact placement regressions; no perceptual acceptance claim."""
import unittest
import cv2,numpy as np
from planar_fv_cartoon_head import PlanarFVCartoonHead,contact_matrix
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead
class PlanarFVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1);cls.old=OccludedTeethCartoonHead();cls.new=PlanarFVCartoonHead()
    def test_non_contact_controls_exact(self):
        for i in [0,1,2,3,4,5,6,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_contact_changes_art_not_face_geometry(self):
        w=np.eye(9)[7];np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
        a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));self.assertGreater(np.count_nonzero(a!=b),0)
        mask=np.ones((512,512),bool);mask[290:380,170:310]=False;np.testing.assert_array_equal(a[mask],b[mask])
    def test_uniform_affine_maps_corners(self):
        t=self.new.target_points(np.eye(9)[7]);corners=np.asarray(self.new.fv_v3_meta['sourceCorners']);m=contact_matrix(t,corners)
        np.testing.assert_allclose(np.c_[corners,np.ones(2)]@m.T,t[[8,0]],atol=1e-4)
        a=m[:,:2];np.testing.assert_allclose(a.T@a,np.eye(2)*np.linalg.det(a),atol=1e-5)
    def test_vertical_jaw_does_not_crush_contact(self):
        t=self.new.target_points(np.eye(9)[7]);other=t.copy();other[1:8,1]+=20;other[9:16,1]-=15
        np.testing.assert_array_equal(contact_matrix(t,self.new.fv_v3_meta['sourceCorners']),contact_matrix(other,self.new.fv_v3_meta['sourceCorners']))
    def test_independent_parts_valid_premultiplied(self):
        parts=self.new.contact_parts(self.new.target_points(np.eye(9)[7]));self.assertEqual(set(parts),{'lip-contact','upper-teeth'})
        self.assertFalse(np.shares_memory(*parts.values()))
        for art in parts.values():
            self.assertTrue(np.isfinite(art).all());self.assertTrue(np.all(art>=0));self.assertTrue(np.all(art[:,:,:3]<=art[:,:,3:4]+1e-5));self.assertGreater(float(art[:,:,3].max()),200)
    def test_degenerate_corners_rejected(self):
        t=self.new.target_points(np.eye(9)[7]);t[0]=t[8]
        with self.assertRaises(ValueError):contact_matrix(t,self.new.fv_v3_meta['sourceCorners'])
if __name__=='__main__':unittest.main()
