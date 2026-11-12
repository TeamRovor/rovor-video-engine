"""Construction diagnostics must not promote a full-head source to a rig."""
import unittest
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from audit_cartoon_construction import source_components,fit_pose
class ConstructionTests(unittest.TestCase):
    def test_component_order_and_missing_heads(self):
        image=np.zeros((120,360,4),np.uint8)
        for x in [10,130,250]:image[10:100,x:x+80]=[230,150,90,255]
        self.assertEqual(source_components(Image.fromarray(image)),[[10,10,80,90],[130,10,80,90],[250,10,80,90]])
        with self.assertRaises(ValueError):source_components(Image.new('RGBA',(512,512)))
    def test_identity_fit_does_not_claim_layer_registration(self):
        cv2.setNumThreads(1);raw=np.array(Image.open(ROOT/'head-rig-v2/head-X.png').convert('RGBA'));y,x=np.where(raw[:,:,3]>=16);box=[int(x.min()),int(y.min()),int(x.max()-x.min()+1),int(y.max()-y.min()+1)];before=raw.copy();aligned,report=fit_pose(raw,box,raw)
        np.testing.assert_array_equal(raw,before);self.assertGreater(report['upperFaceECC'],.999)
        self.assertFalse(report['registrationReady']);self.assertFalse(report['animationReady']);self.assertEqual(aligned.shape,raw.shape)
if __name__=='__main__':unittest.main()
