"""Source-faithful artistic WIP regression: structural-only, no creative approval."""
import hashlib,math,re,unittest
from pathlib import Path
from fabric_protection_v11 import LAYOUTS,SOURCE_SHA,state,svg_frame,FPS

AUDIO=Path(__file__).parent/'original_evan.mp3'
class FabricTests(unittest.TestCase):
    def test_audio_is_original(self):
        self.assertEqual(hashlib.sha256(AUDIO.read_bytes()).hexdigest(),SOURCE_SHA)
    def test_both_aspect_ratios(self):
        self.assertEqual((LAYOUTS['landscape'].width,LAYOUTS['landscape'].height),(960,540))
        self.assertEqual((LAYOUTS['portrait'].width,LAYOUTS['portrait'].height),(540,960))
    def test_source_bounds(self):
        for v in LAYOUTS:
            for t in (0,1,2.5,5.99):self.assertTrue(svg_frame(t,v).startswith('<svg'))
            for t in (-.01,6,math.inf,math.nan):
                with self.assertRaises(ValueError):svg_frame(t,v)
    def test_contact_coordinates_are_same_for_fabric_and_fingers(self):
        for v in LAYOUTS:
            for k in range(0,FPS*6,5):
                t=k/FPS;s=state(t,v);gx,gy=s['contact'];svg=svg_frame(t,v)
                self.assertIn(f'M {gx:.2f} {gy+2:.2f}',svg)
                self.assertIn(f'{gx:.2f} {gy:.2f}',svg)
    def test_arm_reach_is_plausible(self):
        for v,a in LAYOUTS.items():
            for k in range(0,FPS*6,3):
                s=state(k/FPS,v);sx,sy=a.shoulder;ex,ey=s['elbow'];hx,hy=s['hand']
                self.assertLess(math.dist((sx,sy),(ex,ey)),160)
                self.assertLess(math.dist((ex,ey),(hx,hy)),180)
    def test_cloth_progresses_and_finishes(self):
        for v in LAYOUTS:
            values=[state(k/60,v)['coverage'] for k in range(360)]
            self.assertTrue(all(b>=a-1e-8 for a,b in zip(values,values[1:])))
            self.assertLess(values[0],.65)
            self.assertGreater(values[-1],.999)
    def test_painter_face_and_hand_present(self):
        for v in LAYOUTS:
            s=svg_frame(3.3,v)
            self.assertIn('stroke="#1c3143"',s)
            self.assertIn('fill="#253746"',s)
            self.assertIn('id="clothFront"',s)
    def test_interaction_is_not_static(self):
        for v in LAYOUTS:
            self.assertNotEqual(svg_frame(.5,v),svg_frame(2.5,v))
            self.assertNotEqual(svg_frame(2.5,v),svg_frame(5.5,v))
    def test_no_brand_fabrication(self):
        for v in LAYOUTS:
            s=svg_frame(2,v).lower()
            self.assertNotIn('rovor digital',s)
            self.assertNotIn('customer testimony',s)
if __name__=='__main__':unittest.main()