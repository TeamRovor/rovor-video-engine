"""Native SVG story/animation smoke tests — NOT artist or sound sign-off."""
import unittest, hashlib, sys, xml.etree.ElementTree as ET
from pathlib import Path
from PIL import ImageStat,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mechanic_story_v9 import *
class SceneTest(unittest.TestCase):
 def test_actual_contact_plan_all_relevant_frames(self):
  from mechanic_story_v9 import physical_contact_samples
  from contact_audit import audit_contact_track
  for portrait in (False,True):
   r=audit_contact_track(physical_contact_samples(portrait))
   self.assertTrue(r['structural_contact_valid'])
   self.assertGreater(r['pose_count'],20)
 def test_unmodified_source(self):
  self.assertTrue(ORIGINAL.is_file());self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),SOURCE_SHA)
 def test_exact_60fps_frame_range(self):
  self.assertEqual(START_FRAME,8688);self.assertEqual(END_FRAME-START_FRAME,689)
  self.assertEqual(round(START*FPS),START_FRAME);self.assertEqual(round(END*FPS),END_FRAME)
  self.assertEqual(round(CUT*FPS),CUT_FRAME)
 def test_svg_native_both_orientations(self):
  for portrait in [False,True]:
   for frame in [START_FRAME, START_FRAME+70, CUT_FRAME-1,CUT_FRAME,CUT_FRAME+60,END_FRAME-1]:
    svg=svg_at(frame/FPS,portrait)
    root=ET.fromstring(svg);self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
    dims=(1080,1920) if portrait else (1920,1080)
    self.assertEqual((int(root.attrib['width']),int(root.attrib['height'])),dims)
 def test_reject_out_of_bounds(self):
  for t in [-3,START-1/FPS,END,200]:
   with self.assertRaises(AssertionError): svg_at(t)
 def test_each_shot_actually_moves(self):
  for p in [False,True]:
   for a,b in [(145.1,148.5),(151.6,154.9)]:
    x=frame_at(a,p,size='half');y=frame_at(b,p,size='half')
    delta=sum(ImageStat.Stat(ImageChops.difference(x,y)).mean)
    self.assertGreater(delta,1.0,(p,a,b,delta))
 def test_object_first_not_only_pan(self):
  for p in [False,True]:
   x=frame_at(148,p,size='half');y=frame_at(153,p,size='half')
   self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(x,y)).mean),12.)
 def test_genuine_separate_aspect_staging(self):
  for t in [147.0,153.1]:
   a=svg_at(t,False);b=svg_at(t,True)
   self.assertNotEqual(a,b)
   self.assertIn('viewBox="0 0 960 540"',a)
   self.assertIn('viewBox="0 0 540 960"',b)
 def test_no_fake_case_study_or_brand_voice(self):
  source=Path(__file__).with_name('mechanic_story_v9.py').read_text().lower()
  self.assertNotIn('rover digital',source)
  self.assertNotIn('actual customer',source)
if __name__=='__main__':unittest.main(verbosity=2)