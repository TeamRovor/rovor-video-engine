import unittest,hashlib,sys,xml.etree.ElementTree as ET,math
from pathlib import Path
from quote_story_v7 import SOURCE,SHA,SOURCE_START,SOURCE_END,FPS,render_frame,vector_frame,Stage,shot_one,shot_two,shot_three
from PIL import ImageChops,ImageStat
class NarrativeContinuation(unittest.TestCase):
 def test_source_is_authentic(self):
  self.assertTrue(SOURCE.is_file());self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SHA)
 def test_exact_time_span(self):
  self.assertAlmostEqual(SOURCE_END-SOURCE_START,12.8);self.assertEqual(round((SOURCE_END-SOURCE_START)*FPS),768)
 def test_three_distinct_shots(self):
  for p in [False,True]:
   frames=[vector_frame(t,p) for t in [132.3,136.6,141.8]]
   self.assertEqual(len(set(hashlib.sha256(x.encode()).hexdigest() for x in frames)),3)
 def test_native_dimensions_and_svg_validity(self):
  for p in [False,True]:
   for t in [132.0,134.86,134.88,137.4,139.82,139.83,142.1,144.79]:
    root=ET.fromstring(vector_frame(t,p));self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
    expected=(1080,1920) if p else (1920,1080)
    if t in (132,134.88,139.83,144.79):self.assertEqual(render_frame(t,p).size,expected)
 def test_reject_outside_exact_interval(self):
  for t in [131.999,144.8,150]:
   with self.assertRaises(AssertionError): vector_frame(t,False)
 def test_distinct_editing_not_screenshot_pan(self):
  for p in [False,True]:
   a=render_frame(132.1,p,native=False);b=render_frame(137.2,p,native=False);c=render_frame(142.1,p,native=False)
   self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean),10)
   self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(b,c)).mean),10)
 def test_physical_movement_inside_each_shot(self):
  for p in [False,True]:
   for ta,tb in [(132.1,134.5),(135.0,137.9),(140.1,143.9)]:
    a=render_frame(ta,p,native=False);b=render_frame(tb,p,native=False)
    self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean),.15)
 def test_source_privacy_and_brand(self):
  data=Path(__file__).with_name('quote_story_v7.py').read_text()
  self.assertNotIn('fake testimonial',data.lower())
  self.assertNotIn('Rover Digital',data)
if __name__=='__main__':unittest.main(verbosity=2)