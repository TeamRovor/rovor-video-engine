"""Reuse registered-hand guards against the heavier-ink sibling artwork."""
import json,unittest
from PIL import Image
import test_clean_open_palm as base
from relaxed_cartoon_scene import RelaxedWristArm
from cartoon_body import ROOT

class InkPalmTests(unittest.TestCase):
 folder_name='open-palm-ink-v1'
 @classmethod
 def setUpClass(cls):
  base.CleanPalmTests.setUpClass()
  cls.folder=ROOT/cls.folder_name;cls.meta=json.loads((cls.folder/'manifest.json').read_text())
  old=base.CleanPalmTests.arm;cls.arm=RelaxedWristArm(Image.open(cls.folder/'right-skin.png').convert('RGBA'),old.geometry,old);cls.plan=base.CleanPalmTests.plan
 test_proximal_art_source_hash_and_bounds=base.CleanPalmTests.test_proximal_art_source_hash_and_bounds
 test_current_speech_geometry_and_rigid_distal_parent=base.CleanPalmTests.test_current_speech_geometry_and_rigid_distal_parent
 test_distal_proportions_match_opposite_hand=base.CleanPalmTests.test_distal_proportions_match_opposite_hand

class FilteredPalmTests(InkPalmTests):
 folder_name='open-palm-filtered-v1'
 def test_filtered_builder_matches_isolated_footprint_probe(self):
  import tempfile,shutil,hashlib
  from pathlib import Path
  from build_relaxed_cartoon_hand import build
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name in [self.folder_name+'/source-v1.png','body-rig/arm-right.png','source/design-sheet-v1.png','hand-source/right-point-v1.png']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
   source=root/self.folder_name/'source-v1.png';before=source.read_bytes()
   meta=build(root,folder_name=self.folder_name,source_name='source-v1.png',source_wrist=(551,510),source_scale=.192,source_antialias=True)
   self.assertEqual(source.read_bytes(),before)
   self.assertEqual(hashlib.sha256(before).hexdigest(),'c717b774eb0f1ad82a68287c0b6c756365b358a7ff5823aea08708f1ac6c6d0f')
   self.assertAlmostEqual(meta['registrationPrefilter']['sigmaSourcePixels'],2.5557159520920507)
   for name in ['right-skin.png','registered-hand.png','blend-mask.png']:
    self.assertEqual((root/self.folder_name/name).read_bytes(),(self.folder/name).read_bytes())

if __name__=='__main__':unittest.main()
