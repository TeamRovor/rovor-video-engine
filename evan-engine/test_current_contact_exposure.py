"""Current-frame controls and material continuity, not artistic acceptance."""
import json,os,unittest
from pathlib import Path
import cv2,numpy as np
from current_contact_exposure import CurrentContactExposure
from corresponding_lip_exposure import CorrespondingLipExposure
class CurrentContactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=CurrentContactExposure()
 def render_weights(self,w):
  baseline=self.rig.head.weights(w)
  return self.rig.assemble(baseline)
 def test_full_contact_does_not_depend_on_stale_vowel_target(self):
  self.render_weights(np.eye(9)[3]);self.rig.head.last_painted_target[:]=np.nan
  _,a,row=self.render_weights(np.eye(9)[7]);self.assertTrue(np.isfinite(self.rig.last_target).all());self.assertGreater(row['minimumTriangleArea2'],0)
  self.render_weights(np.eye(9)[5]);_,b,_=self.render_weights(np.eye(9)[7]);np.testing.assert_array_equal(np.array(a),np.array(b))
 def test_endpoint_material_and_geometry_have_no_binary_switch(self):
  for endpoint,near in [(0,1e-7),(1,1-1e-7)]:
   images=[]
   for fv in [endpoint,near]:
    _,im,row=self.render_weights(np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv);images.append(np.array(im).astype(int));self.assertEqual(row['continuousFVFallbacks'],0)
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
 def test_zero_fv_reference_samples_preserve_previous_stack(self):
  default=Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json';path=Path(os.environ.get('ROVOR_REFERENCE_PLAN',str(default)))
  if not path.is_file():self.skipTest('Recorded plan unavailable; set ROVOR_REFERENCE_PLAN')
  plan=json.loads(path.read_text());prior=CorrespondingLipExposure()
  for frame in [738,741,742]:
   _,a,_=prior.at(frame/48,plan);_,b,row=self.rig.at(frame/48,plan);self.assertEqual(row['fv'],0);np.testing.assert_array_equal(np.array(a),np.array(b))
 def test_skin_underlap_uses_actual_paint_behind_cavity_without_changing_sources(self):
  from labiodental_construction import FaceCapture
  from guided_jaw_exposure import contour_target_mesh
  r=CurrentContactExposure();r.head=FaceCapture();baseline=r.head.weights(np.eye(9)[3])
  skin=r.head.clean_face.copy();underpaint=np.zeros_like(skin);underpaint[305:365,190:285]=skin[305:365,190:285]
  jaw=r.jaw.copy();_,im,_=r.assemble_target(baseline,*contour_target_mesh(r.head.current_oral,r.head.exposure_skin),underpaint)
  names=list(r.last_parts);self.assertLess(names.index('Face skin underlap'),names.index('Painted mouth cavity backing'))
  np.testing.assert_array_equal(skin,r.head.clean_face);np.testing.assert_array_equal(jaw,r.jaw)
  np.testing.assert_array_equal(r.last_parts['Face skin underlap'],underpaint)
  self.assertEqual(int(np.array(im)[315:340,195:280,3].min()),255)
if __name__=='__main__':unittest.main()
