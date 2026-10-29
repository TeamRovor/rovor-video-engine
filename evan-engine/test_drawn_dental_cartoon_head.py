"""Source isolation, intermediate morph and front-mask regressions."""
import unittest
import cv2,numpy as np
from rooted_floor_cartoon_head import RootedFloorCartoonHead
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
class DrawnDentalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.old=RootedFloorCartoonHead();cls.new=DrawnDentalCartoonHead()
 def test_l_and_other_direct_controls_exact(self):
  self.new.dental_fraction=0
  for i in [0,1,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
 def test_intermediate_surfaces_bounded_without_fallback(self):
  w=np.eye(9)[8];oral=self.new.oral_target(self.new.target_points(w),self.new.geometry['H'][7]-self.new.geometry['H'][6])
  before=self.new.dental_morph_fallbacks
  for d in [.01,.25,.5,.75,.99,1]:
   self.new.dental_fraction=d
   blade,floor=self.new.tongue_parts(w,oral)
   for a in [blade,floor]:
    self.assertTrue(np.isfinite(a).all());self.assertGreaterEqual(a.min(),0);self.assertLessEqual(a[:,:,3].max(),255.0001);self.assertTrue(np.all(a[:,:,:3]<=a[:,:,3:4]+1e-4))
  self.assertEqual(before,self.new.dental_morph_fallbacks)
 def test_dental_surface_stays_inside_lips_and_behind_teeth(self):
  w=np.eye(9)[8];self.new.dental_fraction=1;oral=self.new.oral_target(self.new.target_points(w),self.new.geometry['H'][7]-self.new.geometry['H'][6]);mask=self.new.interior_mask(self.new.cavity_surface(w,oral),w,oral)[:,:,0]
  x=np.asarray(self.old.weights(w));y=np.asarray(self.new.weights(w));changed=np.any(x!=y,axis=2)
  self.assertGreater(changed.sum(),0);self.assertEqual((changed&(mask==0)).sum(),0)
  teeth=self.old.teeth_surface(w,oral)*mask[:,:,None];yy=np.arange(512)[:,None];bottom=np.max(np.where(teeth[:,:,3]>=127.5,yy,-1000),axis=0);protected=(teeth[:,:,3]>=255)&(yy<bottom[None,:]-1.5);np.testing.assert_array_equal(x[protected],y[protected])
  self.assertGreater(int(protected.sum()),0)
if __name__=='__main__':unittest.main()
