import unittest
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_gesture_body import CartoonGestureBody,CartoonSocketBody

class SocketArtworkTests(unittest.TestCase):
    def test_original_art_outside_underarm_mask_is_exact(self):
        old=np.asarray(Image.open(ROOT/'body-rig/torso.png'));new=np.asarray(Image.open(ROOT/'socket-rig/torso.png'));mask=np.asarray(Image.open(ROOT/'socket-rig/patch-mask.png'))
        self.assertTrue(np.array_equal(old[mask==0],new[mask==0]))
        self.assertTrue(np.array_equal(old[:,430:594],new[:,430:594]))
        self.assertTrue(np.array_equal(old[650:],new[650:]))
        self.assertGreater(int(np.any(old!=new,axis=2).sum()),1000)
    def test_original_gesture_keeps_original_torso(self):
        baseline=CartoonGestureBody();patched=CartoonSocketBody()
        self.assertTrue(np.array_equal(np.asarray(baseline.torso),np.asarray(Image.open(ROOT/'body-rig/torso.png'))))
        self.assertFalse(np.array_equal(np.asarray(baseline.torso),np.asarray(patched.torso)))
if __name__=='__main__':unittest.main()
