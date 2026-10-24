"""Control transfer and input safety; not artistic or lip-sync acceptance."""
import unittest
import numpy as np
from guided_jaw_exposure import SOURCE,contour_target_mesh,target_mesh

class ContourJawTests(unittest.TestCase):
 def setUp(self):
  self.oral=np.zeros((32,2),np.float32);angles=np.arange(16)*np.pi/8
  self.oral[:16]=np.column_stack([228.5+34.5*np.cos(angles),325+10*np.sin(angles)])
  self.oral[16:]=self.oral[:16];self.skin=np.zeros((48,2),np.float32);self.skin[46,1]=394
 def test_intermediate_arch_control_survives_with_center_and_corners_fixed(self):
  a,_=contour_target_mesh(self.oral,self.skin);old,_=target_mesh(self.oral,self.skin)
  oral=self.oral.copy();oral[2,1]+=3
  b,_=contour_target_mesh(oral,self.skin);legacy,_=target_mesh(oral,self.skin)
  np.testing.assert_array_equal(old,legacy)
  self.assertGreater(float(np.max(abs(a-b))),1)
  np.testing.assert_array_equal(a[SOURCE[:,1]>=394],b[SOURCE[:,1]>=394])
 def test_lip_rounding_does_not_squeeze_jaw_skin_sideways(self):
  baseline,_=contour_target_mesh(self.oral,self.skin);edges=(SOURCE[:,0]<=181)|(SOURCE[:,0]>=298)
  for width,offset in [(69,0),(40,-3),(24,3)]:
   oral=self.oral.copy();oral[:,0]=228.5+offset+(oral[:,0]-228.5)*width/69
   target,minimum=contour_target_mesh(oral,self.skin)
   np.testing.assert_array_equal(target[:,0],SOURCE[:,0]);np.testing.assert_allclose(target[edges],baseline[edges],atol=.00004);self.assertGreater(minimum,0)
 def test_actual_center_is_not_clipped_to_two_pose_release_range(self):
  center=np.flatnonzero((SOURCE[:,0]==228.5)&(SOURCE[:,1]==328.5))[0]
  for lower in [323,332,340,368,374]:
   oral=self.oral.copy();oral[:9,1]=325+(lower-325)*np.sin(np.arange(9)*np.pi/8)
   target,minimum=contour_target_mesh(oral,self.skin)
   self.assertAlmostEqual(float(target[center,1]),lower,places=4);self.assertGreater(minimum,0)
 def test_rejects_nonfinite_and_unordered_arch(self):
  for value in [float('nan'),self.oral[1,0]+1]:
   oral=self.oral.copy();oral[2,0]=value
   with self.assertRaises(ValueError):contour_target_mesh(oral,self.skin)
  skin=self.skin.copy();skin[46,1]=np.nan
  with self.assertRaises(ValueError):target_mesh(self.oral,skin)

if __name__=='__main__':unittest.main()
