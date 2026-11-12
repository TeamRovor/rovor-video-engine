import unittest
import numpy as np,cv2
from aperture_response_cartoon_head import ApertureResponseCartoonHead,direct_oral_target
from painted_contour_cartoon_head import PaintedContourCartoonHead
from cartoon_head import TRIANGLES,area,POINTS
class ApertureResponseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.new=ApertureResponseCartoonHead();cls.old=PaintedContourCartoonHead()
 def test_positive_mesh_contact_through_vowels_and_random_mix(self):
  rng=np.random.default_rng(1234);cases=list(np.eye(9));cases+=list(rng.dirichlet(np.ones(9),size=1000));tri=[ids for ids in TRIANGLES if max(ids)<32]
  for w in cases:
   target=self.new.target_points(w);before=target.copy();ap=sum(v*(self.new.geometry[s][7]-self.new.geometry[s][6]) for v,s in zip(w,'XABCDEFGH'))
   oral=direct_oral_target(target,ap)
   self.assertGreater(min(area(oral,ids) for ids in tri),0)
   np.testing.assert_array_equal(target,before);np.testing.assert_array_equal(oral[32:],target[32:]);np.testing.assert_array_equal(oral[:,0],target[:,0])
   np.testing.assert_array_equal(oral[[0,8]],target[[0,8]])
 def test_no_secondary_threshold_jump_for_fixed_shape(self):
  previous=None
  for aperture in np.linspace(1,12,111):
   o=direct_oral_target(POINTS['C'],aperture);height=np.ptp(o[:16,1])
   if previous is not None:self.assertLessEqual(abs(height-previous),.101)
   previous=height
 def test_interiors_cannot_escape_inner_lip_contour(self):
  oral=direct_oral_target(POINTS['C'],20)
  cavity=np.full((512,512,4),255,np.float32)
  mask=self.new.interior_mask(cavity,np.eye(9)[3],oral)[:,:,0]
  ys,xs=np.where(mask>0)
  self.assertGreater(len(xs),0)
  for x,y in zip(xs,ys):
   # Partly covered edge pixels may straddle the analytic contour.
   distance=cv2.pointPolygonTest(oral[16:32],(float(x),float(y)),True)
   self.assertGreaterEqual(distance,-.5)
   if mask[y,x]>=.5:self.assertGreaterEqual(distance,0)
  closed=direct_oral_target(POINTS['A'],1)
  self.assertEqual(float(self.new.interior_mask(cavity,np.eye(9)[1],closed).max()),0)
 def test_fv_mixed_weights_remain_exact(self):
  for fv in [.001,.1,.5,1.]:
   w=np.zeros(9);w[7]=fv;w[1]=1-fv
   np.testing.assert_array_equal(np.array(self.old.weights(w)),np.array(self.new.weights(w)))
if __name__=='__main__':unittest.main()
