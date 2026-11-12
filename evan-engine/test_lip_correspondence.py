"""Source preservation and actual contact/release material coverage."""
import json,os,unittest
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from lip_surface_correspondence import source_mesh
from corresponding_lip_exposure import CorrespondingLipExposure

class LipCorrespondenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);default=Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json';path=Path(os.environ.get('ROVOR_REFERENCE_PLAN',str(default)));cls.plan=json.loads(path.read_text()) if path.is_file() else None;cls.rig=CorrespondingLipExposure() if cls.plan is not None else None
 def test_source_registration_does_not_repaint_or_move_chin_art(self):
  from guided_jaw_exposure import SOURCE
  raw=np.array(Image.open(ROOT/'jaw-overlap-v1/Jaw.png').convert('RGBA'));before=raw.copy();points,report=source_mesh(raw)
  np.testing.assert_array_equal(raw,before);np.testing.assert_array_equal(points[SOURCE[:,1]>=375],SOURCE[SOURCE[:,1]>=375]);self.assertGreater(report['minimumSourceTriangleArea2'],0);self.assertFalse(report['sourceAlphaModified'])
 def test_planned_contact_has_material_coverage_without_chin_or_identity_changes(self):
  if self.plan is None:self.skipTest('Recorded reference plan unavailable; set ROVOR_REFERENCE_PLAN')
  before,after,row=self.rig.at(738/48,self.plan);self.assertGreater(row['oralAlphaCounts']['Previous']['below240'],0);self.assertEqual(row['oralAlphaCounts']['Both']['below240'],0)
  np.testing.assert_array_equal(np.array(before)[:288],np.array(after)[:288]);np.testing.assert_array_equal(np.array(before)[288:315,190:280],np.array(after)[288:315,190:280]);np.testing.assert_array_equal(np.array(before)[400:],np.array(after)[400:])
 def test_release_samples_retain_coverage_and_four_actual_planes(self):
  if self.plan is None:self.skipTest('Recorded reference plan unavailable; set ROVOR_REFERENCE_PLAN')
  for frame in [741,742]:
   _,_,row=self.rig.at(frame/48,self.plan);self.assertEqual(row['oralAlphaCounts']['Both']['below240'],0);self.assertEqual(len(self.rig.last_parts),4);self.assertIn('Painted mouth cavity backing',self.rig.last_parts)
if __name__=='__main__':unittest.main()
