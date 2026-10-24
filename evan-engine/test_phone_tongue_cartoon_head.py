"""Phone isolation and geometry regressions, not phonetic/artistic acceptance."""
import unittest
import cv2,numpy as np
from phone_tongue_cartoon_head import PhoneTongueCartoonHead,phone_blade_matrix,dental_fraction
from rooted_floor_cartoon_head import RootedFloorCartoonHead,rooted_blade_matrix
class PhoneTongueTests(unittest.TestCase):
 def test_kernel_partition_and_fallback(self):
  p={'alignment':{'status':'acoustic'},'phonemes':[{'phone':'L','start':0,'end':.1},{'phone':'DH','start':.3,'end':.4}]}
  self.assertEqual(dental_fraction(.03,p),0);self.assertEqual(dental_fraction(.33,p),1);self.assertEqual(dental_fraction(1,p),0)
  p['alignment']['status']='fallback';self.assertEqual(dental_fraction(.33,p),0)
 def test_root_and_no_dental_exact(self):
  for h in np.linspace(0,1,21):
   np.testing.assert_array_equal(phone_blade_matrix(h,0),rooted_blade_matrix(h))
   for d in np.linspace(0,1,11):
    m=phone_blade_matrix(h,d);np.testing.assert_allclose(m@np.array([237,354,1]),[237,354],atol=2e-5);self.assertGreater(m[1,1],0)
  self.assertLess(phone_blade_matrix(1,1)[1,1],phone_blade_matrix(1,0)[1,1])
 def test_direct_controls_exact_and_context_restored(self):
  cv2.setNumThreads(1);a=RootedFloorCartoonHead();b=PhoneTongueCartoonHead()
  for i in [0,1,7,8]:np.testing.assert_array_equal(a.weights(np.eye(9)[i]),b.weights(np.eye(9)[i]))
  # Exception cleanup prevents a failed acoustic frame contaminating later calls.
  with self.assertRaises(KeyError):b.at(.33,{'alignment':{'status':'acoustic'},'phonemes':[{'phone':'DH','start':.3,'end':.4}]})
  self.assertEqual(b.dental_fraction,0)
 def test_dental_pixels_stay_inside_mouth_and_behind_teeth(self):
  cv2.setNumThreads(1);a=RootedFloorCartoonHead();b=PhoneTongueCartoonHead();b.dental_fraction=1
  w=np.eye(9)[8];target=b.target_points(w);aperture=b.geometry['H'][7]-b.geometry['H'][6];oral=b.oral_target(target,aperture)
  mask=b.interior_mask(b.cavity_surface(w,oral),w,oral)[:,:,0]
  x=np.asarray(a.weights(w));y=np.asarray(b.weights(w));changed=np.any(x!=y,axis=2)
  self.assertGreater(int(changed.sum()),0);self.assertEqual(int((changed&(mask==0)).sum()),0)
  teeth=b.teeth_surface(w,oral)*mask[:,:,None];np.testing.assert_array_equal(x[teeth[:,:,3]>=255],y[teeth[:,:,3]>=255])
  for i in [0,1,7]:np.testing.assert_array_equal(a.weights(np.eye(9)[i]),b.weights(np.eye(9)[i]))
if __name__=='__main__':unittest.main()
