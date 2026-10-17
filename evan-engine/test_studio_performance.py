import json
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from studio_performance import validate_direction,direction_pose,directed_hand_exposures,JOINT_DEFAULTS,describe
from cartoon_rig_blockout import frame_svg,state_at

ROOT=Path(__file__).resolve().parent

class StudioPerformanceTests(unittest.TestCase):
    def setUp(self):self.cues=json.loads((ROOT/'studio-direction-example.json').read_text())

    def test_hold_anticipation_and_zero_random_wiggle(self):
        self.assertEqual(len(validate_direction(self.cues)),4)
        self.assertEqual(direction_pose(.12,self.cues),JOINT_DEFAULTS)
        self.assertEqual(direction_pose(.3,self.cues),JOINT_DEFAULTS)
        self.assertEqual(direction_pose(.55,self.cues)['handR'],'open')
        self.assertEqual(direction_pose(.86,self.cues)['headTilt'],-4)
        self.assertEqual(direction_pose(.9,self.cues),direction_pose(.98,self.cues))
        self.assertEqual(direction_pose(1.2,self.cues)['handR'],'open')
        self.assertEqual(direction_pose(2.75,self.cues)['handR'],'point')

    def test_hand_drawings_transition_in_shared_wrist_space(self):
        at=.55
        self.assertEqual(directed_hand_exposures('R',.2,self.cues),[('relaxed',1.)])
        half=directed_hand_exposures('R',at-.06,self.cues)
        self.assertEqual(half,[('relaxed',.5),('open',.5)])
        self.assertEqual(directed_hand_exposures('R',.8,self.cues),[('open',1.)])

    def test_engineering_frame_consumes_independent_editorial_timeline(self):
        root=ET.fromstring(frame_svg(.8,direction=self.cues))
        self.assertEqual(root.attrib['data-performance-status'],'editorial-beat-blockout')
        ids={n.attrib['id']:n for n in root.iter() if 'id' in n.attrib}
        self.assertEqual(ids['hand-R'].attrib['data-hand-pose'],'open')
        self.assertEqual(ids['hand-L'].attrib['data-hand-pose'],'relaxed')
        self.assertEqual(state_at(.8,direction=self.cues).headTilt,-4)
        self.assertFalse(describe(self.cues)['animationApproved'])

    def test_hard_fails_on_invalid_authored_timing(self):
        for patch in [{'at':float('nan')},{'at':.03,'anticipate':.1},{'origin':'ai-inferred'},
                      {'pose':{'jawOpen':1}},{'pose':{'handR':'unknown'}},{'at':.8}]:
            cues=json.loads(json.dumps(self.cues))
            if 'origin' in patch:cues['origin']=patch['origin']
            else:cues['beats'][0].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):validate_direction(cues)

if __name__=='__main__':unittest.main()