"""Geometry/attachment/default preservation, not a hand-animation quality score."""
import unittest,numpy as np
from cartoon_index import IndexRig
from compact_cartoon_index import CompactIndexRig
from compact_cartoon_scene import compact_controls
from cartoon_scene import scene_controls
from test_cartoon_scene import PLAN,areas
class CompactIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=IndexRig();cls.new=CompactIndexRig()
    def test_all_scene_frames_keep_orientation(self):
        ids=np.array(self.new.triangles);rest=areas(self.new.vertices,ids)
        for i in range(489):
            v=self.new.posed_vertices(compact_controls(i/48,PLAN)['index'])
            self.assertGreater(float((areas(v,ids)/rest).min()),.05)
    def test_projected_joint_attachment(self):
        for angles in [[-7,42,24.5],[-3.5,21,12.25],[0,0,0]]:
            a,b,c=self.new.matrices(angles)
            np.testing.assert_allclose(a@np.r_[self.new.joints[1],1],b@np.r_[self.new.joints[1],1],atol=.001)
            np.testing.assert_allclose(b@np.r_[self.new.joints[2],1],c@np.r_[self.new.joints[2],1],atol=.001)
    def test_point_pose_pixels_remain_exact(self):
        np.testing.assert_array_equal(self.old.render([0,0,0]),self.new.render([0,0,0]))
    def test_other_acting_controls_unchanged(self):
        for i in range(489):
            a=scene_controls(i/48,PLAN);b=compact_controls(i/48,PLAN)
            for key in a:
                if key!='index':self.assertEqual(a[key],b[key])
    def test_aggressive_unreviewed_curl_rejected(self):
        for angles in [[-10,60,35],[0,95,70],[0,0,float('nan')]]:
            with self.assertRaises(ValueError):self.new.posed_vertices(angles)
