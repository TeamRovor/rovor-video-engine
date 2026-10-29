import unittest,cv2,numpy as np
from thumbs_up_plane import ThumbsUpPlane
class ThumbsUpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.plane=ThumbsUpPlane()
 def test_parent_translation_is_exact_and_source_unmodified(self):
  source=self.plane.source.copy();a=self.plane.pose(np.eye(3));m=np.eye(3);m[1,2]=10;b=self.plane.pose(m)
  np.testing.assert_array_equal(b[10:],a[:-10]);np.testing.assert_array_equal(source,self.plane.source);self.assertGreater(a[:,:,3].sum(),0);self.assertTrue(np.isfinite(a).all())
 def test_measured_wrist_guides_register_without_reflection(self):
  p=self.plane;r=p.registration;points=np.array(r['sourceWristGuide']);out=(points-r['sourceAnchor'])@p.linear.T+r['targetWrist']
  np.testing.assert_allclose(out.mean(axis=0),r['targetWrist']);self.assertAlmostEqual(float(np.linalg.norm(out[1]-out[0])),47.);self.assertGreater(np.linalg.det(p.linear),0)
 def test_padded_body_margin_retains_translated_hand(self):
  a=self.plane.pose(np.eye(3));m=np.eye(3);m[0,2]=200;b=self.plane.pose(m)
  self.assertEqual(a.shape,(1536,1464,4));np.testing.assert_array_equal(b[:,200:],a[:,:-200]);self.assertAlmostEqual(float(a[:,:,3].sum()),float(b[:,:,3].sum()),delta=.1)
 def test_off_canvas_parent_is_empty(self):
  m=np.eye(3);m[0,2]=10000;self.assertEqual(np.count_nonzero(self.plane.pose(m)),0)
 def test_invalid_parent_rejected(self):
  reflected=np.eye(3);reflected[0,0]=-1;scaled=np.eye(3);scaled[0,0]=2
  for m in [np.eye(2),np.full((3,3),np.nan),np.zeros((3,3)),reflected,scaled]:
   with self.assertRaises(ValueError):self.plane.pose(m)
if __name__=='__main__':unittest.main()
