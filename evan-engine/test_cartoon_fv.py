import unittest
import numpy as np
from fv_cartoon_head import FVContactHead
from expressive_cartoon_head import ExpressiveCartoonHead
from cartoon_head import TRIANGLES,SYMBOLS
class FVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.new=FVContactHead();cls.old=ExpressiveCartoonHead()
    def test_non_fv_poses_are_unchanged(self):
        for i in [0,1,3,5,8]:self.assertTrue(np.array_equal(np.asarray(self.new.weights(np.eye(9)[i])),np.asarray(self.old.weights(np.eye(9)[i]))))
    def test_new_contact_preserves_upper_face(self):
        a=np.asarray(self.new.weights(np.eye(9)[7]));b=np.asarray(self.old.weights(np.eye(9)[7]));self.assertTrue(np.array_equal(a[:292],b[:292]))
    def test_new_landmarks_have_no_interpolation_foldovers(self):
        ids=np.asarray(TRIANGLES)
        for a in self.new.points.values():
            for b in self.new.points.values():
                for w in np.linspace(0,1,21):
                    points=a*(1-w)+b*w
                    for target in (points,self.new.contact_target(points)):
                        tri=target[ids];x=tri[:,1]-tri[:,0];y=tri[:,2]-tri[:,0]
                        self.assertGreater(float(np.min(x[:,0]*y[:,1]-x[:,1]*y[:,0])),0)
    def test_teeth_and_lips_are_separate_local_surfaces(self):
        for image in self.new.fv_layers.values():self.assertEqual(image[:307,:,3].max(),0);self.assertEqual(image[341:,:,3].max(),0);self.assertGreater(image[:,:,3].max(),200)
if __name__=='__main__':unittest.main()
