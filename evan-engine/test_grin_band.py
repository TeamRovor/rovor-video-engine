"""Postroll tooth-band registration; no speaking anatomy acceptance."""
import unittest,cv2,numpy as np
from grin_tooth_plane import GrinToothPlane
from separated_oral_review import MaterialCapture,inner_arch,inner_oral_coverage
class GrinBandTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plane=GrinToothPlane();cls.upper=np.column_stack([np.linspace(195,285,9),np.full(9,321.)]);cls.lower=cls.upper+[0,10]
 def test_leaves_lower_counterspace(self):
  p=self.plane.pose_grin_band(self.upper,self.lower)
  self.assertGreater(float(p[321:326,220:260,3].mean()),180)
  self.assertLess(float(p[328:332,220:260,3].mean()),2)
 def test_exact_vertical_parent_translation(self):
  a=self.plane.pose_grin_band(self.upper,self.lower);b=self.plane.pose_grin_band(self.upper+[0,10],self.lower+[0,10])
  np.testing.assert_array_equal(a[:-10],b[10:])
 def test_invalid_arches_and_source_guides(self):
  for bad in [np.zeros((8,2)),np.full((9,2),np.nan),self.upper[::-1]]:
   for a,b in [(bad,self.lower),(self.upper,bad)]:
    with self.assertRaises(ValueError):self.plane.pose_grin_band(a,b)
  with self.assertRaises(ValueError):self.plane.pose_grin_band(self.upper,self.upper-[0,1])
  p=GrinToothPlane();p.band_guides[4,2]=p.band_guides[4,1]
  with self.assertRaises(ValueError):p.pose_grin_band(self.upper,self.lower)
 def test_actual_closed_lumen_and_source_immutability(self):
  h=MaterialCapture();h.weights(np.eye(9)[1]);source=self.plane.source.copy();oral=h.current_oral
  clipped=self.plane.pose_grin_band(inner_arch(oral,True),inner_arch(oral))*inner_oral_coverage(oral)
  self.assertEqual(np.count_nonzero(clipped),0);np.testing.assert_array_equal(source,self.plane.source)
if __name__=='__main__':unittest.main()
