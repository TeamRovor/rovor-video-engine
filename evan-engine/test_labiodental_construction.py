"""Component ownership and source invariants, not animation acceptance."""
import unittest
import cv2,numpy as np
from labiodental_construction import LabiodentalConstruction
from layered_cartoon_head import straight
class ConstructionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=LabiodentalConstruction()
 def test_release_moves_jaw_while_incisors_and_upper_lip_stay_fixed(self):
  r=self.rig;a,contact=r.pose(0);teeth=r.last_parts['Fixed upper incisors'].copy();cap=r.last_parts['Drawn upper-lip cap'].copy();jaw=r.last_parts['Drawn jaw and lower lip'].copy();b,release=r.pose(1)
  np.testing.assert_array_equal(teeth,r.last_parts['Fixed upper incisors']);np.testing.assert_array_equal(cap,r.last_parts['Drawn upper-lip cap']);self.assertFalse(np.array_equal(jaw,r.last_parts['Drawn jaw and lower lip']));self.assertEqual(release['lowerLipY']-contact['lowerLipY'],7)
  np.testing.assert_array_equal(np.array(a)[:315],np.array(b)[:315]);self.assertGreater(min(contact['minimumTriangleArea2'],release['minimumTriangleArea2']),0)
 def test_cap_underlaps_face_and_sources_remain_unchanged(self):
  r=self.rig;jaw=r.jaw.copy();cap=r.cap.copy();im,_=r.pose(.5);names=list(r.last_parts)
  self.assertLess(names.index('Fixed upper incisors'),names.index('Drawn jaw and lower lip'));self.assertLess(names.index('Drawn upper-lip cap'),names.index('Upper face and cheek wings'))
  expected=np.rint(straight(r.face)).astype('uint8');np.testing.assert_array_equal(np.array(im)[304:315,220:250],expected[304:315,220:250]);np.testing.assert_array_equal(jaw,r.jaw);np.testing.assert_array_equal(cap,r.cap)
if __name__=='__main__':unittest.main()
