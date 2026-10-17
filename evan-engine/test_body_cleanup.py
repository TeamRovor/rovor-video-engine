import unittest
import numpy as np
from PIL import Image
from build_cartoon_body import ROOT,register_body


class BodyCleanupTests(unittest.TestCase):
    def test_hidden_rgb_cannot_drive_registration(self):
        original=Image.open(ROOT/'source/setup-v1.png').convert('RGBA')
        raw=np.asarray(original).copy();hidden=raw[:,:,3]==0
        raw[hidden,:3]=np.random.default_rng(12).integers(0,256,(int(hidden.sum()),3),dtype='uint8')
        _,report=register_body(original,Image.fromarray(raw))
        self.assertGreater(report['ecc'],.999)
        np.testing.assert_allclose(report['matrix'],[[1,0,0],[0,1,0]],atol=.003)

    def test_repair_is_bounded_and_original_neck_fragment_removed(self):
        original=np.asarray(Image.open(ROOT/'body-rig/torso.png').convert('RGBA'))
        repaired=np.asarray(Image.open(ROOT/'body-rig/torso-cleanup-v2.png').convert('RGBA'))
        allowed=np.zeros(original.shape[:2],bool);allowed[295:340,443:575]=True
        for x,y,u,v in ((324,445,414,558),(610,445,700,558)):allowed[y:v,x:u]=True
        np.testing.assert_array_equal(original[~allowed],repaired[~allowed])
        np.testing.assert_array_equal(repaired[:340,:,3],original[:340,:,3])
        self.assertEqual(repaired[324,445,3],original[324,445,3])
        self.assertEqual(repaired[350,500,3],original[350,500,3])


if __name__=='__main__':unittest.main()
