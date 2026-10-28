"""Geometry, source ownership and isolation; not anatomical acceptance."""
import unittest,json,hashlib
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_digit_curl import CartoonDigitCurl

class DigitCurlTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=CartoonDigitCurl()
 def test_partition_rest_and_source_preservation(self):
  meta=json.loads((ROOT/'digit-curl-v1/manifest.json').read_text());source=ROOT/'open-palm-filtered-v1/source-v1.png';self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sourceSha256']);raw=np.array(Image.open(source));rest=np.array(self.rig.render({name:[0,0,0]for name in self.rig.digits}));visible=raw[:,:,3]>0;np.testing.assert_array_equal(raw[visible],rest[visible]);np.testing.assert_array_equal(raw[:,:,3],rest[:,:,3])
 def test_continuous_four_digit_meshes_and_fixed_roots(self):
  minimum=1e9
  for u in np.linspace(0,1,481):
   for name,d in self.rig.digits.items():
    c=np.array([12,16,8]if name=='thumb'else[-8,-30,-18])*u;posed=d.posed_vertices(c);fixed=(d.vertices-d.joints[0])@d.axis<=0;np.testing.assert_allclose(posed[fixed],d.vertices[fixed],atol=1e-4);p=posed[np.array(d.triangles)];v=p[:,1:]-p[:,0,None];minimum=min(minimum,float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()))
  self.assertGreater(minimum,11)
  ring=self.rig.digits['ring'];before=ring.posed_vertices([0,0,0]);self.rig.digits['little'].posed_vertices([-8,-30,-18]);np.testing.assert_array_equal(before,ring.posed_vertices([0,0,0]))
 def test_invalid_controls(self):
  for value in [[0,0], [float('nan'),0,0], [0,36,0]]:
   with self.assertRaises(ValueError):self.rig.digits['little'].posed_vertices(value)
  with self.assertRaises(ValueError):self.rig.render({'thumb':[0,0,0]})

if __name__=='__main__':unittest.main()
