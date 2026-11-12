"""Protect cheek ink, source rest, jaw movement and oral separation."""
import unittest
import numpy as np
from anchored_cartoon_head import AnchoredCartoonHead
from separated_cartoon_head import SeparatedCartoonHead
from cartoon_head import POINTS,TRIANGLES,warp

class AnchoredSkinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=SeparatedCartoonHead();cls.new=AnchoredCartoonHead()
    def test_rounded_poses_keep_sideburn_pixels_at_source(self):
        rest=np.asarray(self.new.weights(np.eye(9)[0]))
        for i in [5,6]:
            out=np.asarray(self.new.weights(np.eye(9)[i]))
            np.testing.assert_array_equal(out[294:320,296:333],rest[294:320,296:333])
    def test_rest_pixels_exact(self):
        np.testing.assert_array_equal(self.old.weights(np.eye(9)[0]),self.new.weights(np.eye(9)[0]))
    def test_oral_material_pixels_still_follow_vowel_mesh(self):
        for i in [3,5,6,8]:
            w=np.eye(9)[i];target=self.new.target_points(w);ap=self.new.geometry['XABCDEFGH'[i]][7]-self.new.geometry['XABCDEFGH'[i]][6]
            oral=self.new.oral_target(target,ap)
            cavity=warp(self.new.layers['cavity-outline'],POINTS['C'],oral,2)
            interior=cavity[:,:,3]==255
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w))
            np.testing.assert_array_equal(a[interior],b[interior])
            # Legacy cubic sampling overshoots alpha above 255 at some ink
            # edges: it leaks up to one quantization level of underlying skin.
            # Keep the opaque core exact and bound that separate fringe issue.
            fringe=cavity[:,:,3]>255
            np.testing.assert_allclose(a[fringe].astype(int),b[fringe].astype(int),atol=1,rtol=0)
    def test_jaw_anchors_are_not_frozen(self):
        rest=self.new.skin_target(np.eye(9)[0],POINTS['X'])
        opened=self.new.skin_target(np.eye(9)[4],POINTS['D'])
        old=self.old.skin_target(np.eye(9)[4],POINTS['D'])
        np.testing.assert_array_equal(opened[32:],old[32:])
        self.assertGreater(float(opened[46,1]-rest[46,1]),15)
    def test_source_skin_mesh_has_no_foldovers(self):
        ids=np.asarray(TRIANGLES)
        for a in np.eye(9):
            for b in np.eye(9):
                for fraction in [0,.25,.5,.75,1]:
                    w=a*fraction+b*(1-fraction);target=self.new.target_points(w);skin=self.new.skin_target(w,target)
                    tri=skin[ids];u=tri[:,1]-tri[:,0];v=tri[:,2]-tri[:,0]
                    self.assertGreater(float(np.min(u[:,0]*v[:,1]-u[:,1]*v[:,0])),0)
