import unittest
import cv2,numpy as np
from painted_contour_cartoon_head import PaintedContourCartoonHead
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from cartoon_head import TRIANGLES,area
class PaintedContourTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.new=PaintedContourCartoonHead();cls.old=ConstructionSkinCartoonHead()
 def test_source_annulus_and_contact_target_are_positive(self):
  tri=[ids for ids in TRIANGLES if max(ids)<32]
  self.assertGreater(min(area(self.new.painted_points,ids) for ids in tri),0)
  for u in np.linspace(0,1,101):
   w=np.zeros(9);w[1]=1-u;w[5]=u;target=self.new.target_points(w);aperture=sum(w[i]*(self.new.geometry[s][7]-self.new.geometry[s][6]) for i,s in enumerate('XABCDEFGH'))
   oral=self.new.oral_target(target,aperture)
   self.assertGreater(min(area(oral,ids) for ids in tri),0)
 def test_closed_sprite_cannot_affect_painted_composite(self):
  self.new.painted_rim=np.zeros((8,8,4),np.float32);zero=self.new.painted_rim.copy();ink=zero+255
  w=np.zeros(9);w[1]=1
  a=self.new.composite_oral(zero,zero,zero,zero,zero,zero,1,w)
  b=self.new.composite_oral(zero,zero,zero,zero,zero,ink,1,w)
  np.testing.assert_array_equal(a,b)
 def test_fv_endpoint_matches_previous_profile(self):
  for fv in [.001,.1,.5,1.]:
   w=np.zeros(9);w[7]=fv;w[1]=1-fv
   np.testing.assert_array_equal(np.array(self.old.weights(w)),np.array(self.new.weights(w)))
if __name__=='__main__':unittest.main()
