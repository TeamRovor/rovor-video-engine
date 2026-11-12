"""Independent control and source safety, not anatomy/animation acceptance."""
import unittest
import cv2,numpy as np
from lower_lip_plane import LowerLipPlane,arch_surface

class LowerLipTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.lip=LowerLipPlane()
 def arch(self):
  x=np.linspace(198,274,9);return np.column_stack([x,321+4*np.sin(np.linspace(0,np.pi,9))]).astype('float32')
 def test_pressure_compresses_only_material_thickness_and_keeps_source(self):
  source=self.lip.source.copy();arch=self.arch();before=arch.copy();a=self.lip.pose(arch,0);b=self.lip.pose(arch,1)
  self.assertLess(float(b[:,:,3].sum()),float(a[:,:,3].sum())*.7);self.assertFalse(np.array_equal(a,b))
  np.testing.assert_array_equal(self.lip.source,source);np.testing.assert_array_equal(arch,before)
  contacts=[]
  for part in [a,b]:
   y,x=np.where(part[:,:,3]>127.5);self.assertGreaterEqual(x.min(),197);self.assertLessEqual(x.max(),275);self.assertGreaterEqual(y.min(),319)
   values=part[:,236,3];top=np.flatnonzero(values>=127.5)[0];contacts.append(float(top-1+(127.5-values[top-1])/(values[top]-values[top-1])))
  self.assertLess(abs(contacts[0]-contacts[1]),.5)
 def test_jaw_edge_underlaps_lip_without_target_frame_quantization(self):
  arch=self.arch();source=self.lip.source.copy();a=self.lip.jaw_arch(arch,0);b=self.lip.jaw_arch(arch,1)
  np.testing.assert_array_equal(a[:,0],arch[:,0]);np.testing.assert_array_equal(a[[0,-1]],arch[[0,-1]])
  self.assertTrue(np.all(a[:,1]>=b[:,1]));self.assertTrue(np.all(b[:,1]>=arch[:,1]))
  delta=np.array([.0001,.0002],np.float32);shift=self.lip.jaw_arch(arch+delta,0)
  np.testing.assert_allclose(shift,a+delta,atol=.00004);np.testing.assert_array_equal(source,self.lip.source)
 def test_bad_pressure_and_arch_reject_without_nan_render(self):
  for p in [-1,1.1,float('nan')]:
   with self.assertRaises(ValueError):self.lip.pose(self.arch(),p)
  for value in [float('nan'),190]:
   arch=self.arch();arch[2,0]=value
   with self.assertRaises(ValueError):self.lip.pose(arch,0)
  with self.assertRaises(ValueError):arch_surface(self.lip.source,[[198,321],[198,322]],self.arch())
  with self.assertRaises(ValueError):arch_surface(self.lip.source,self.lip.edge,self.arch(),0)

if __name__=='__main__':unittest.main()
