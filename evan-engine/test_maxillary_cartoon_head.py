import unittest
import cv2,numpy as np
from maxillary_cartoon_head import MaxillaryCartoonHead,maxillary_oral_target
from continuous_fv_cartoon_head import ContinuousFVCartoonHead
from cartoon_head import TRIANGLES,POINTS,area
class MaxillaryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.new=MaxillaryCartoonHead();cls.old=ContinuousFVCartoonHead()
 def test_mesh_and_scope(self):
  rng=np.random.default_rng(8123);tri=[ids for ids in TRIANGLES if max(ids)<32]
  for w in list(np.eye(9))+list(rng.dirichlet(np.ones(9),1000)):
   t=self.new.target_points(w);before=t.copy();ap=sum(v*(self.new.geometry[s][7]-self.new.geometry[s][6]) for v,s in zip(w,'XABCDEFGH'));o=maxillary_oral_target(t,ap)
   self.assertGreater(min(area(o,ids) for ids in tri),0);np.testing.assert_array_equal(o[:,0],t[:,0]);np.testing.assert_array_equal(o[32:],t[32:]);np.testing.assert_array_equal(o[[0,8]],t[[0,8]]);np.testing.assert_array_equal(t,before)
 def test_tooth_plane_area_retained_before_occlusion(self):
  w=np.eye(9)[3];areas=[]
  for ap in [1,5,10,20,33]:
   oral=maxillary_oral_target(POINTS['C'],ap);art=self.new.teeth_surface(w,oral);areas.append(float(art[:,:,3].sum()/255))
  self.assertLess(max(areas)-min(areas),1)
  source=self.new.layers['upper-teeth'];self.assertEqual(int(np.count_nonzero(source[:300,:,3])),0)
 def test_fv_endpoint_and_entry_limit(self):
  w=np.eye(9)[7];np.testing.assert_array_equal(np.array(self.old.weights(w)),np.array(self.new.weights(w)))
  w=np.eye(9)[3];x=np.array(self.new.weights(w)).astype(int);w[3]=1-1e-7;w[7]=1e-7;y=np.array(self.new.weights(w)).astype(int);self.assertLessEqual(abs(x-y).max(),2)
if __name__=='__main__':unittest.main()
