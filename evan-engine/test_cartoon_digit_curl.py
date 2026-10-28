"""Geometry, source ownership and isolation; not anatomical acceptance."""
import unittest,json,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw
from cartoon_body import ROOT
from cartoon_digit_curl import CartoonDigitCurl,partial_curl_controls

class DigitCurlTests(unittest.TestCase):
 folder_name='digit-curl-v1'
 minimum_area2=11
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=CartoonDigitCurl(folder_name=cls.folder_name)
 def test_partition_rest_and_source_preservation(self):
  meta=json.loads((ROOT/self.folder_name/'manifest.json').read_text());source=ROOT/'open-palm-filtered-v1/source-v1.png';self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sourceSha256']);raw=np.array(Image.open(source));rest=np.array(self.rig.render({name:[0,0,0]for name in self.rig.digits}));visible=raw[:,:,3]>0;np.testing.assert_array_equal(raw[visible],rest[visible]);np.testing.assert_array_equal(raw[:,:,3],rest[:,:,3])
 def test_continuous_four_digit_meshes_and_fixed_roots(self):
  minimum=1e9
  for u in np.linspace(0,1,481):
   for name,d in self.rig.digits.items():
    c=np.array([12,16,8]if name=='thumb'else[-8,-30,-18])*u;posed=d.posed_vertices(c);fixed=(d.vertices-d.joints[0])@d.axis<=0;np.testing.assert_allclose(posed[fixed],d.vertices[fixed],atol=1e-4);p=posed[np.array(d.triangles)];v=p[:,1:]-p[:,0,None];minimum=min(minimum,float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()))
  self.assertGreater(minimum,self.minimum_area2)
  ring=self.rig.digits['ring'];before=ring.posed_vertices([0,0,0]);self.rig.digits['little'].posed_vertices([-8,-30,-18]);np.testing.assert_array_equal(before,ring.posed_vertices([0,0,0]))
 def test_invalid_controls(self):
  for value in [[0,0], [float('nan'),0,0], [0,36,0]]:
   with self.assertRaises(ValueError):self.rig.digits['little'].posed_vertices(value)
  with self.assertRaises(ValueError):self.rig.render({'thumb':[0,0,0]})

class DigitCurlV2Tests(DigitCurlTests):
 folder_name='digit-curl-v2'
 minimum_area2=0
 def test_no_static_distal_contour_remnants(self):
  meta=json.loads((ROOT/self.folder_name/'manifest.json').read_text());palm=np.array(self.rig.palm);yy,xx=np.mgrid[:palm.shape[0],:palm.shape[1]];mask=Image.new('L',self.rig.palm.size);ImageDraw.Draw(mask).polygon(meta['indexProtectionPolygon'],fill=255);index=np.array(mask)>0;distal=np.zeros(index.shape,bool)
  for name,d in self.rig.digits.items():
   if name=='thumb':continue
   offset=np.stack([xx-d.joints[0][0],yy-d.joints[0][1]],axis=2);s=offset@d.axis;q=offset@d.normal;distal|=(s>90)&(s<np.linalg.norm(np.array(meta['digits'][name]['tip'])-d.joints[0])+35)&(abs(q)<50)
  self.assertFalse(((palm[:,:,3]>127)&distal&~index).any())
 def test_bounded_stroke_avoids_index_and_full_stroke_is_detected(self):
  meta=json.loads((ROOT/self.folder_name/'manifest.json').read_text());palm=np.array(self.rig.palm);yy,xx=np.mgrid[:palm.shape[0],:palm.shape[1]];mask=Image.new('L',self.rig.palm.size);ImageDraw.Draw(mask).polygon(meta['indexProtectionPolygon'],fill=255);index=(np.array(mask)>0)&(palm[:,:,3]>127)&((xx-960)*.86+(yy-790)*.51>80)
  for u in [0,.05,.1,.15,.2,1]:
   overlap=0;alphas=[]
   for name,d in self.rig.digits.items():
    saved=d.source.copy();s=(xx-d.joints[0][0])*d.axis[0]+(yy-d.joints[0][1])*d.axis[1]
    try:
     d.source[s<90]=0;angles=partial_curl_controls(u)[name]if u<=.2 else(np.array([12,16,8]if name=='thumb'else[-8,-30,-18])*u).tolist();im=d.render(angles,canvas=self.rig.palm.size,pad=0,source_view=True);alpha=np.array(im)[:,:,3]>127;alphas.append(alpha);overlap+=int((alpha&index).sum())
    finally:d.source=saved
   if u<=.2:
    self.assertEqual(overlap,0);self.assertEqual(sum(int((a&b).sum())for i,a in enumerate(alphas)for b in alphas[i+1:]),0)
   else:self.assertGreater(overlap,10000)


 def test_partial_amount_bounds(self):
  for amount in [-.001,.201,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):partial_curl_controls(amount)

if __name__=='__main__':unittest.main()
