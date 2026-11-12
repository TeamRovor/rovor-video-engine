import unittest,copy
import numpy as np
from expressive_cartoon_head import ExpressiveCartoonHead,brow_controls,expression_events
from layered_cartoon_head import LayeredCartoonHead
class BrowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.head=ExpressiveCartoonHead();cls.base=LayeredCartoonHead()
    def test_speech_and_features_outside_forehead_are_exact(self):
        w=np.eye(9)[3];a=np.asarray(self.base.weights(w));b=np.asarray(self.head.weights(w,dict(rightRaise=7,leftRaise=-1)))
        valid=np.ones((512,512),bool);valid[180:239,150:335]=False
        self.assertTrue(np.array_equal(a[valid],b[valid]))
    def test_brows_are_independent(self):
        w=np.eye(9)[0];a=np.asarray(self.head.weights(w));b=np.asarray(self.head.weights(w,dict(rightRaise=7)))
        self.assertTrue(np.array_equal(a[:,:230],b[:,:230]));self.assertGreater(int(np.any(a[:,240:]!=b[:,240:],axis=2).sum()),100)
    def test_word_cues_follow_alignment_without_mutation(self):
        p={'words':[dict(word='tiny',scriptIndex=4,start=2,end=2.3)]};before=copy.deepcopy(p)
        self.assertEqual(expression_events(p)[0]['scriptIndex'],4);self.assertGreater(brow_controls(2.2,p)['rightRaise'],6);self.assertEqual(brow_controls(3,p)['rightRaise'],0);self.assertEqual(p,before)
    def test_authored_motion_has_no_frame_jump(self):
        p={'words':[dict(word='tiny',scriptIndex=4,start=2,end=2.3)]};values=np.array([list(brow_controls(float(t),p).values()) for t in np.arange(1,3,.001)])
        self.assertLess(float(np.abs(np.diff(values,axis=0)).max()),.08)
if __name__=='__main__':unittest.main()
