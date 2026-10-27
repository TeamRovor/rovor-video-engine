"""Reuse registered-hand guards against the heavier-ink sibling artwork."""
import json,unittest
from PIL import Image
import test_clean_open_palm as base
from relaxed_cartoon_scene import RelaxedWristArm
from cartoon_body import ROOT

class InkPalmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  base.CleanPalmTests.setUpClass()
  cls.folder=ROOT/'open-palm-ink-v1';cls.meta=json.loads((cls.folder/'manifest.json').read_text())
  old=base.CleanPalmTests.arm;cls.arm=RelaxedWristArm(Image.open(cls.folder/'right-skin.png').convert('RGBA'),old.geometry,old);cls.plan=base.CleanPalmTests.plan
 test_proximal_art_source_hash_and_bounds=base.CleanPalmTests.test_proximal_art_source_hash_and_bounds
 test_current_speech_geometry_and_rigid_distal_parent=base.CleanPalmTests.test_current_speech_geometry_and_rigid_distal_parent
 test_distal_proportions_match_opposite_hand=base.CleanPalmTests.test_distal_proportions_match_opposite_hand

if __name__=='__main__':unittest.main()
