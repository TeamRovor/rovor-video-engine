import unittest,sys,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from estimate_desk_v12 import frame,FRAME_COUNT,FPS,START_FRAME,END_FRAME,SOURCE_SHA,sm
class TestDeskAnimation(unittest.TestCase):
 def test_source(self):
  self.assertEqual(hashlib.sha256((Path(__file__).parent/'original.mp3').read_bytes()).hexdigest(),SOURCE_SHA)
 def test_exact_frames(self):self.assertEqual((START_FRAME,END_FRAME,FRAME_COUNT),(1752,2484,732))
 def test_dual_stage_art(self):
  for view,dims in [('landscape',('960','540')),('portrait',('540','960'))]:
   xml=ET.fromstring(frame(2.0,view));self.assertEqual((xml.attrib['width'],xml.attrib['height']),dims)
 def test_acting_not_identical(self):
  for v in ('landscape','portrait'):
   self.assertNotEqual(frame(.2,v),frame(2.1,v));self.assertNotEqual(frame(2.1,v),frame(4.4,v));self.assertNotEqual(frame(7.4,v),frame(10.1,v))
 def test_paper_stamps_reveal_after_contacts(self):
  for v in ('landscape','portrait'):
   self.assertNotIn('QUALITY WORK',frame(4.3,v));self.assertIn('QUALITY WORK',frame(7.5,v));self.assertIn('FREE ESTIMATES',frame(10.4,v))
 def test_papers_separately_staged(self):self.assertNotEqual(frame(10.5,'landscape').split('viewBox')[1][:30],frame(10.5,'portrait').split('viewBox')[1][:30])
 def test_stamp_continuity_at_former_jump(self):
  # At prior cut 8.35s the entire SVG must not teleport across paper.
  for v in ('landscape','portrait'):
   self.assertNotEqual(frame(8.2,v),frame(8.5,v))
   import re
   a=frame(8.34,v);b=frame(8.36,v)
   def pos(x):
    hit=re.findall(r'<g transform="translate\(([0-9.]+) ([0-9.]+)\) rotate\(-7',x)
    self.assertTrue(hit)
    return tuple(float(v) for v in hit[-1])
   x,y=pos(a);xx,yy=pos(b)
   self.assertLess(abs(x-xx)+abs(y-yy),18)
 def test_always_parseable(self):
  for v in ('landscape','portrait'):
   for k in (0,39,100,141,200,280,352,421,455,568,602,700,731):ET.fromstring(frame(k/FPS,v))
 def test_arm_connected_to_picture_boundary(self):
  for v in ('landscape','portrait'):
   rendered=frame(7.1,v)
   self.assertIn('M -79 -45',rendered)
   self.assertIn("Q -60 14",rendered)
 def test_scope_explanation_not_fake_client(self):
  body=frame(11,v='landscape') if False else frame(11,'landscape')
  self.assertIn('DETAILS NOT PROVIDED',body);self.assertNotIn('CLIENT TESTIMONIAL',body)
if __name__=='__main__':unittest.main()