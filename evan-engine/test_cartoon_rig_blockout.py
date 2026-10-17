import unittest
import xml.etree.ElementTree as ET
from cartoon_rig_blockout import frame_svg, state_at, controls_at, clamp, hand_svg, hand_exposures

class CartoonBlockoutTests(unittest.TestCase):
    def test_svg_real_components_and_independent_bone_hierarchy(self):
        root=ET.fromstring(frame_svg(.76));ns='{http://www.w3.org/2000/svg}'
        ids={node.attrib['id']:node for node in root.iter() if 'id' in node.attrib}
        for component in ('head','jaw','oral-interior','upper-teeth','tongue','upper-lip','lower-lip','torso'):
            self.assertIn(component,ids)
        for side in 'LR':
            self.assertIn('upper-arm-'+side,ids)
            self.assertIn('elbow-'+side,ids)
            self.assertIn('forearm-'+side,ids)
            self.assertIn('wrist-'+side,ids)
            self.assertIn('hand-'+side,ids)
            self.assertEqual(ids['hand-'+side].attrib['data-hand-pose'],state_at(.76).__dict__['hand'+side])
        self.assertEqual(root.attrib['data-art-status'],'engineering-blockout')
        self.assertEqual(root.attrib['data-official-brand'],'false')

    def test_body_arms_act_separately(self):
        rest=state_at(0);present=state_at(.76);point=state_at(2.75)
        self.assertNotEqual(rest.shoulderR,present.shoulderR)
        self.assertEqual(rest.handL,'relaxed')
        self.assertEqual(present.handR,'open')
        self.assertEqual(point.handR,'point')
        self.assertNotEqual(present.elbowL,present.elbowR)
        self.assertNotEqual(frame_svg(.76),frame_svg(2.75))

    def test_acoustic_control_sample_interpolation(self):
        p={'controls':[dict(time=0,jawOpen=0,lipSeal=1,lipRound=0,lipSpread=0,lowerLipContact=0,tongueVisible=0),
                       dict(time=1,jawOpen=1,lipSeal=0,lipRound=1,lipSpread=.4,lowerLipContact=.7,tongueVisible=.8)]}
        mid=controls_at(.5,p)
        self.assertAlmostEqual(mid['jawOpen'],.5)
        self.assertAlmostEqual(mid['lowerLipContact'],.35)
        root=ET.fromstring(frame_svg(.5,p))
        self.assertEqual(root.attrib['data-speech-status'],'speech-plan-controls')

    def test_hand_pose_exposures_are_registered_and_normalized(self):
        for side in 'LR':
            for tick in range(0,96):
                poses=hand_exposures(side,tick/24)
                self.assertAlmostEqual(sum(w for _,w in poses),1,places=6)
                self.assertTrue(all(w>=0 for _,w in poses))
        self.assertEqual(len(hand_exposures('R',.58)),2)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):clamp(float('nan'))
        with self.assertRaises(ValueError):frame_svg(-1)
        with self.assertRaises(ValueError):controls_at(0,{'controls':[]})

    def test_all_hand_pose_types(self):
        self.assertEqual(len(set(hand_svg(p) for p in ('relaxed','open','point','explain','fist'))),5)
        with self.assertRaises(ValueError):hand_svg('unknown')

if __name__=='__main__': unittest.main()