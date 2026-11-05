"""Independent lip-edge/chin controls in the review-only jaw surface."""
import unittest
import numpy as np
from guided_jaw_exposure import SOURCE,target_mesh,GuidedJawExposure
from PIL import Image
from cartoon_head import POINTS

class GuidedJawControlTests(unittest.TestCase):
 def setUp(self):
  self.oral=POINTS['B'].copy();self.oral[8]=[194,325];self.oral[0]=[263,325];self.oral[20]=[228.5,328.5];self.skin=POINTS['X'].copy();self.skin[46,1]=394
 def test_chin_motion_leaves_lip_edge_control_independent(self):
  a,_=target_mesh(self.oral,self.skin);skin=self.skin.copy();skin[46,1]+=10;b,_=target_mesh(self.oral,skin)
  np.testing.assert_array_equal(a[SOURCE[:,1]<=335],b[SOURCE[:,1]<=335]);np.testing.assert_allclose((b-a)[SOURCE[:,1]>=394,1],10,atol=1e-5)
 def test_lip_motion_leaves_chin_row_and_source_unchanged(self):
  before=SOURCE.copy();a,_=target_mesh(self.oral,self.skin);oral=self.oral.copy();oral[20,1]+=12;b,_=target_mesh(oral,self.skin)
  np.testing.assert_array_equal(a[SOURCE[:,1]>=394],b[SOURCE[:,1]>=394]);self.assertGreater(float((b-a)[SOURCE[:,0]==228.5,1].max()),10);np.testing.assert_array_equal(SOURCE,before)
 def test_opening_crest_is_rounded_rather_than_linear_v(self):
  a,_=target_mesh(self.oral,self.skin);oral=self.oral.copy();oral[20,1]+=12;b,_=target_mesh(oral,self.skin);dy=(b-a)[:,1]
  center=dy[(SOURCE[:,0]==228.5)&(SOURCE[:,1]==325)][0];shoulder=dy[(SOURCE[:,0]==211)&(SOURCE[:,1]==325)][0]
  self.assertGreater(shoulder,center*.65)
 def test_unsupported_full_fv_does_not_reuse_stale_oral_target(self):
  class UnsupportedHead:
   painted_rim=None
   def at(self,t,plan):return Image.new('RGBA',(512,512))
  rig=GuidedJawExposure.__new__(GuidedJawExposure);rig.head=UnsupportedHead()
  with self.assertRaisesRegex(ValueError,'No full F/V jaw assembly'):rig.at(0,{})
if __name__=='__main__':unittest.main()
