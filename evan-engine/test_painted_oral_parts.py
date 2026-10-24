import unittest
import cv2
import numpy as np
from PIL import Image
from build_painted_oral_parts import match_cavity


class ContourBackingTests(unittest.TestCase):
    def fixtures(self):
        rim=np.zeros((160,240,4),np.uint8)
        cv2.ellipse(rim,(120,80),(90,50),0,0,360,(70,20,10,255),6)
        cavity=np.zeros_like(rim)
        cv2.ellipse(cavity,(110,70),(60,35),0,0,360,(110,35,30,255),-1)
        return rim,cavity

    def test_different_source_contour_backs_aperture_without_mutation(self):
        rim,cavity=self.fixtures();original=cavity.copy()
        out,envelope=match_cavity(Image.fromarray(cavity),Image.fromarray(rim))
        interior=cv2.erode(envelope,np.ones((7,7),np.uint8))>=250
        self.assertTrue(np.all(np.asarray(out)[:,:,3][interior]>=240))
        self.assertTrue(np.array_equal(cavity,original))
        self.assertTrue(np.all(np.asarray(out)[:,:,3][envelope==0]==0))

    def test_open_or_filled_rim_rejected(self):
        rim,cavity=self.fixtures()
        broken=rim.copy();broken[:,115:125]=0
        with self.assertRaises(ValueError):match_cavity(Image.fromarray(cavity),Image.fromarray(broken))
        solid=rim.copy();cv2.ellipse(solid,(120,80),(90,50),0,0,360,(70,20,10,255),-1)
        with self.assertRaises(ValueError):match_cavity(Image.fromarray(cavity),Image.fromarray(solid))


if __name__=='__main__':unittest.main()
