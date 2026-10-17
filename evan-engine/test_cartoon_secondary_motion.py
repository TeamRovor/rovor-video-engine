"""Secondary action tests: deliberate lag, no random motion on holds."""
from dataclasses import dataclass
import unittest, xml.etree.ElementTree as ET
from cartoon_secondary_motion import secondary_at
from cartoon_rig_blockout import frame_svg, state_at

@dataclass
class Pose:
    headTilt:float=0
    headNod:float=0
    bodyLean:float=0

def sample(t):
    return Pose(headTilt=min(t,1.)*9,headNod=min(t,1.)*3,bodyLean=min(t,1.)*8)

class SecondaryTests(unittest.TestCase):
    def test_velocity_follow_through_then_rest(self):
        self.assertEqual(secondary_at(0,sample).hairTilt,0)
        moving=secondary_at(.6,sample)
        self.assertNotEqual(moving.hairTilt,0)
        self.assertNotEqual(moving.tieTilt,0)
        held=secondary_at(1.5,sample)
        self.assertEqual(held.hairTilt,0)
        self.assertEqual(held.tieTilt,0)
        self.assertEqual(held.tieLift,0)
    def test_clamped_for_extreme_directed_pose(self):
        def extreme(t):return Pose(500*t,-90*t,400*t)
        result=secondary_at(.2,extreme)
        self.assertLessEqual(abs(result.hairTilt),5.5)
        self.assertLessEqual(abs(result.tieTilt),7.0)
    def test_scene_remains_editable_and_no_random_secondary(self):
        xml=frame_svg(.75)
        self.assertEqual(xml,frame_svg(.75))
        root=ET.fromstring(xml)
        ids={n.attrib['id'] for n in root.iter() if 'id' in n.attrib}
        self.assertIn('tie-secondary',ids)
        self.assertIn('hair-front',ids)
    def test_bad_time_fails(self):
        for v in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):secondary_at(v,sample)

if __name__=='__main__':unittest.main()