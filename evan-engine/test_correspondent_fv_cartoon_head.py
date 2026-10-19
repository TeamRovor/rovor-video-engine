"""F/V envelope correspondence regressions, not anatomy/performance approval."""
import unittest
import cv2,numpy as np
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from planar_fv_cartoon_head import PlanarFVCartoonHead
class CorrespondentFVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1);cls.old=PlanarFVCartoonHead();cls.new=CorrespondentFVCartoonHead();cls.new.capture_fv_registration=True
    def test_all_pure_controls_exact(self):
        for i in range(9):np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_mixed_registration_reduces_silhouette_disagreement(self):
        for s in [.2,.5,.8]:
            self.new.weights(np.eye(9)[3]*(1-s)+np.eye(9)[7]*s);r=self.new.last_fv_registration
            self.assertLess(r['afterDisagreementPixels'],r['beforeDisagreementPixels']*.4);self.assertTrue(r['validPremultiplied'])
    def test_change_stays_local_and_geometry_exact(self):
        w=np.eye(9)[3]*.5+np.eye(9)[7]*.5;np.testing.assert_array_equal(self.new.target_points(w),self.old.target_points(w))
        a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));outside=np.ones((512,512),bool);outside[295:390,175:305]=False
        np.testing.assert_array_equal(a[outside],b[outside]);self.assertGreater(np.count_nonzero(a!=b),0)
    def test_degenerate_reference_falls_back_exactly(self):
        face=np.ones((32,32,4),np.float32)*255;blank=np.zeros_like(face);w=np.eye(9)[3]*.5+np.eye(9)[7]*.5;n=self.new.fv_correspondence_fallbacks
        a=self.old.composite_oral(face,blank,blank,blank,blank,blank,20,w);b=self.new.composite_oral(face,blank,blank,blank,blank,blank,20,w)
        np.testing.assert_array_equal(a,b);self.assertEqual(self.new.fv_correspondence_fallbacks,n+1)
if __name__=='__main__':unittest.main()
