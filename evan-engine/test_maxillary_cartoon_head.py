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
 def test_separating_dental_material_preserves_original_composite(self):
  from layered_cartoon_head import over
  w=np.eye(9)[8]*.7+np.eye(9)[3]*.3;oral=self.new.oral_target(self.new.target_points(w),20)
  try:
   self.new.dental_fraction=0;teeth=self.new.rigid_teeth_surface(w,oral)
   for fraction in [1e-7,.5,1]:
    self.new.dental_fraction=fraction;blade,_=self.new.tongue_parts(w,oral)
    alpha=teeth[:,:,3];ys=np.arange(512,dtype=np.float32)[:,None];bottom=np.max(np.where(alpha>=127.5,ys,-1000),axis=0)
    edge=np.clip((ys-(bottom[None,:]-1.5))/1.5,0,1)*(alpha/255)
    np.testing.assert_array_equal(over(teeth,blade,fraction*edge[:,:,None]),self.new.rigid_teeth_surface(w,oral))
  finally:self.new.dental_fraction=0
 def test_fv_endpoint_and_entry_limit(self):
  w=np.eye(9)[7];np.testing.assert_array_equal(np.array(self.old.weights(w)),np.array(self.new.weights(w)))
  w=np.eye(9)[3];x=np.array(self.new.weights(w)).astype(int);w[3]=1-1e-7;w[7]=1e-7;y=np.array(self.new.weights(w)).astype(int);self.assertLessEqual(abs(x-y).max(),2)
if __name__=='__main__':unittest.main()
