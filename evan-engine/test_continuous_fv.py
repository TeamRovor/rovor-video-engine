import unittest
import numpy as np,cv2
from continuous_fv_cartoon_head import ContinuousFVCartoonHead
from aperture_response_cartoon_head import ApertureResponseCartoonHead
from cartoon_head import TRIANGLES,area
class ContinuousFVTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.new=ContinuousFVCartoonHead();cls.old=ApertureResponseCartoonHead()
 def test_zero_and_full_contact_endpoints_exact(self):
  for i in [1,3,5,7]:
   w=np.eye(9)[i];np.testing.assert_array_equal(np.array(self.old.weights(w)),np.array(self.new.weights(w)))
 def test_no_epsilon_switch_at_contact_entry(self):
  w=np.eye(9)[3];x=np.array(self.new.weights(w)).astype(int);w[3]=1-1e-7;w[7]=1e-7;y=np.array(self.new.weights(w)).astype(int)
  self.assertLessEqual(abs(x-y).max(),2)
  old0=np.array(self.old.weights(np.eye(9)[3])).astype(int);old1=np.array(self.old.weights(w)).astype(int)
  self.assertGreater(abs(old0-old1).max(),100)
 def test_no_epsilon_switch_at_full_contact(self):
  w=np.eye(9)[7];x=np.array(self.new.weights(w)).astype(int);w[7]=1-1e-7;w[3]=1e-7;y=np.array(self.new.weights(w)).astype(int)
  self.assertLessEqual(abs(x-y).max(),2)
 def test_geometry_mixture_positive_and_nonoral_controls_exact(self):
  head=self.new;tri=[ids for ids in TRIANGLES if max(ids)<32]
  for fv in np.linspace(0,1,101):
   w=np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv;target=head.target_points(w);ap=sum(v*(head.geometry[s][7]-head.geometry[s][6]) for v,s in zip(w,'XABCDEFGH'))
   previous=head._fv_strength;head._fv_strength=float(fv)
   try:oral=head.oral_target(target,ap)
   finally:head._fv_strength=previous
   self.assertGreater(min(area(oral,ids) for ids in tri),0);np.testing.assert_array_equal(oral[32:],target[32:]);np.testing.assert_array_equal(oral[:,0],target[:,0])
if __name__=='__main__':unittest.main()
