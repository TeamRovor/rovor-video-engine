"""Independent tooth sampling/aperture checks, not anatomical approval."""
import unittest
import cv2,numpy as np
from dental_fv_cartoon_head import DentalFVCartoonHead,tooth_anchor
class DentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.head=DentalFVCartoonHead();cls.head.capture_dental=True
    def test_source_aperture_retains_original_support(self):
        support=self.head.contact_art['upper-teeth'][:,:,3]>0
        np.testing.assert_array_equal(self.head.contact_window[support],np.ones(support.sum()))
    def test_subpixel_anchor_tracks_translation(self):
        a=np.zeros((40,40,4),np.float32);a[12:19,10:25]=255
        b=cv2.warpAffine(a,np.array([[1,0,2],[0,1,3]],np.float32),(40,40))
        np.testing.assert_allclose(tooth_anchor(b)-tooth_anchor(a),[2,3],atol=1e-5)
    def test_aperture_occludes_rigid_material_without_uniform_fade(self):
        t=self.head.target_points(np.eye(9)[7]);contact=self.head.contact_surface(t);yy,xx=np.mgrid[:512,:512].astype('float32');field=(xx,320+(yy-320)*2)
        self.head.registered_contact_surface(contact,field,np.eye(9)[7]*.5+np.eye(9)[3]*.5);r=self.head.last_dental
        self.assertLess(r['afterMatteCoverage'],r['beforeMatteCoverage']*.95);self.assertEqual(r['materialAlphaBeforeMatte'],255);self.assertTrue(r['validPremultiplied']);self.assertGreater(r['rigidAlphaVariance'],r['stretchedAlphaVariance'])
    def test_empty_guide_uses_existing_contact(self):
        contact=self.head.contact_surface(self.head.target_points(np.eye(9)[7]));self.head._dental_parts['upper-teeth'][:]=0;yy,xx=np.mgrid[:512,:512].astype('float32');n=self.head.dental_fallbacks
        actual=self.head.registered_contact_surface(contact,(xx,yy),np.eye(9)[7]*.5+np.eye(9)[3]*.5)
        np.testing.assert_array_equal(actual,contact);self.assertEqual(self.head.dental_fallbacks,n+1)
if __name__=='__main__':unittest.main()
