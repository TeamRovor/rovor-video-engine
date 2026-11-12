"""Source-layer/unchanged-control safeguards, not anatomical approval."""
import unittest,numpy as np
from material_cartoon_head import MaterialCartoonHead
from sculpted_contact_head import SculptedContactHead
from cartoon_head import SYMBOLS,TRIANGLES,warp,POINTS
class SculptedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=MaterialCartoonHead();cls.new=SculptedContactHead()
    def test_non_contact_pure_poses_remain_exact(self):
        for i in range(9):
            if i!=7:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_target_geometry_unchanged(self):
        for w in np.eye(9):np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
    def test_contact_changes_only_mouth(self):
        w=np.eye(9)[7];a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));mask=np.ones(a.shape[:2],bool);mask[300:385,180:295]=False
        np.testing.assert_array_equal(a[mask],b[mask]);self.assertGreater(np.count_nonzero(a!=b),0)
    def test_separate_surfaces_and_volume_occlusion(self):
        w=np.eye(9)[7]*.45+np.eye(9)[2]*.55;target=self.new.target_points(w);parts=self.new.contact_parts(target)
        self.assertEqual(set(parts),{'lips','teeth','lower_lip'})
        for art in parts.values():self.assertGreater(np.count_nonzero(art[:,:,3]>.1),0)
        ap=target[20,1]-target[28,1];cavity=warp(self.new.layers['cavity-outline'],POINTS['C'],self.new.oral_target(target,ap),2)
        interior=cavity[:,:,3]>254.99
        self.assertLess(float(parts['lower_lip'][:,:,3][interior].max()),.02)
