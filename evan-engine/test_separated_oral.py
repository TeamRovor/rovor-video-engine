"""Fresh material/geometry, geometric crown occlusion and source safety."""
import unittest,cv2,numpy as np
from separated_oral_review import SeparatedOralReview,inner_arch,rounded_oral_arch

class SeparatedOralTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=SeparatedOralReview()
 def pose(self,fv):
  w=np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv;baseline=self.rig.head.weights(w);return self.rig.assemble(baseline)
 def test_inner_arch_preserves_actual_registered_xy_pairs(self):
  oral=np.arange(96,dtype=np.float32).reshape(48,2)
  np.testing.assert_array_equal(inner_arch(oral),oral[16:25][::-1])
  np.testing.assert_array_equal(inner_arch(oral,True),np.vstack([oral[24:32],oral[16]]))
 def test_rounded_arcs_preserve_corners_x_and_nonoral_controls(self):
  from maxillary_cartoon_head import maxillary_oral_target
  from cartoon_head import POINTS,TRIANGLES,area
  for aperture in [1,5,20,40]:
   oral=maxillary_oral_target(POINTS['C'],aperture)
   for strength in [0,.001,.5,1]:
    result=rounded_oral_arch(oral,aperture,strength)
    np.testing.assert_array_equal(result[:,0],oral[:,0]);np.testing.assert_array_equal(result[32:],oral[32:]);np.testing.assert_allclose(result[[0,8,16,24]],oral[[0,8,16,24]],atol=.00004)
    self.assertGreater(min(area(result,ids) for ids in TRIANGLES if max(ids)<32),0)
  for strength in [-1,1.1,float('nan')]:
   with self.assertRaises(ValueError):rounded_oral_arch(oral,20,strength)
 def test_contact_endpoint_is_fresh_and_continuous(self):
  source=self.rig.lower.source.copy()
  for pair in [(0,1e-7),(1-1e-7,1)]:
   images=[]
   for fv in pair:
    self.rig.head.last_painted_target=np.full((48,2),np.nan);im,row=self.pose(fv);images.append(np.array(im).astype(int));self.assertGreater(row['minimumTriangleArea2'],0);self.assertEqual(len(row['planes']),10);self.assertFalse(row['bakedMouthInUpperCarrier'])
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
  np.testing.assert_array_equal(source,self.rig.lower.source)
 def test_crown_is_clipped_geometrically_and_upper_identity_preserved(self):
  im,row=self.pose(.4);parts=self.rig.last_parts;mask=self.rig.head.review_interior[:,:,0]
  self.assertEqual(float(parts['Rigid upper incisors'][:,:,3][mask==0].max()),0)
  self.assertTrue(row['upper288Exact']);self.assertLessEqual(row['noseMaximumChange'],1)
  self.assertGreater(float(parts['Independent lower lip'][:,:,3].sum()),0)
  self.assertGreater(float(parts['Independent upper-lip cap'][:,:,3].sum()),0)
 def test_nonrounded_capture_does_not_change_original_head_output(self):
  from current_contact_exposure import CurrentContactHead
  original=CurrentContactHead();w=np.eye(9)[3]*.6+np.eye(9)[7]*.4
  np.testing.assert_array_equal(np.array(original.weights(w)),np.array(self.rig.head.weights(w)))
 def test_dental_tip_is_separate_and_crown_material_is_unchanged(self):
  w=np.eye(9)[8]*.7+np.eye(9)[3]*.3
  def pose():return self.rig.assemble(self.rig.head.weights(w))
  pose();crown=self.rig.head.review_teeth.copy();source=self.rig.head.dental_tip.copy()
  try:
   images=[]
   for fraction in [0,1e-7,1-1e-7,1]:
    self.rig.head.dental_fraction=fraction;im,row=pose();images.append(np.array(im).astype(int))
    np.testing.assert_array_equal(crown,self.rig.head.review_teeth)
    self.assertTrue(row['upper288Exact'])
   self.assertGreater(float(self.rig.last_parts['Front dental tongue tip'][:,:,3].sum()),0)
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
   self.assertLessEqual(int(abs(images[2]-images[3]).max()),2)
   np.testing.assert_array_equal(source,self.rig.head.dental_tip)
  finally:self.rig.head.dental_fraction=0

if __name__=='__main__':unittest.main()
