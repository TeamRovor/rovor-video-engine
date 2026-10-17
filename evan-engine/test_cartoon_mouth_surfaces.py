"""Mouth geometry tests are engineering safety checks, not visual acceptance."""
import unittest, math, xml.etree.ElementTree as ET
from dataclasses import replace
from cartoon_mouth_surfaces import mouth_svg, mouth_geometry
from cartoon_rig_blockout import State, frame_svg

class MouthSurfacesTests(unittest.TestCase):
    def test_contact_modes_and_geometry(self):
        self.assertEqual(mouth_geometry(jawOpen=.8,lipSeal=1).mode,'bilabial')
        self.assertEqual(mouth_geometry(jawOpen=.5,lowerLipContact=1).mode,'labiodental')
        self.assertEqual(mouth_geometry(jawOpen=.5,tongueVisible=1).mode,'alveolar')
        self.assertEqual(mouth_geometry(jawOpen=.6,lipRound=1).mode,'rounded')
        self.assertLess(mouth_geometry(jawOpen=.6,lipRound=1).width,
                        mouth_geometry(jawOpen=.6,lipRound=0).width)
        self.assertLess(mouth_geometry(jawOpen=.7,lipSeal=1).aperture,1)
    def test_closed_mask_and_one_outline(self):
        for seal in (0,.4,1):
            raw=mouth_svg(State(jawOpen=.8,lipSeal=seal))
            root=ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">'+raw+'</svg>')
            ns='{http://www.w3.org/2000/svg}'
            clipped=root.find(".//*[@id='mouth-surface-clip']")
            self.assertIsNotNone(clipped)
            path=clipped.find(ns+'path').attrib['d']
            self.assertEqual(path.count('M '),1)
            self.assertEqual(path.count(' Z'),1)
            self.assertIsNotNone(root.find(".//*[@id='upper-teeth']"))
            self.assertIsNotNone(root.find(".//*[@id='tongue']"))
            if seal==1:
                self.assertEqual(root.find(".//*[@id='oral-interior']").attrib['opacity'],'0.0000')
                self.assertEqual(root.find(".//*[@id='upper-lip']").attrib['opacity'],'0.0000')
    def test_poses_preserve_independent_layers_without_nonfinite(self):
        for jaw in (0,.25,.75,1):
            for contact in (0,.4,1):
                for seal in (0,.5,1):
                    s=State(jawOpen=jaw,lowerLipContact=contact,lipSeal=seal)
                    raw=mouth_svg(s)
                    self.assertNotIn('nan',raw.lower())
                    root=ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">'+raw+'</svg>')
                    ids=[e.attrib['id'] for e in root.iter() if 'id' in e.attrib]
                    self.assertEqual(len(ids),len(set(ids)))
    def test_bad_control_rejected(self):
        for bad in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):mouth_geometry(jawOpen=bad)
    def test_full_frame_layer_registration(self):
        root=ET.fromstring(frame_svg(.7))
        ids=[e.attrib['id'] for e in root.iter() if 'id' in e.attrib]
        self.assertEqual(len(ids),len(set(ids)))
        for id in ('head','jaw','mouth-rig','oral-interior','upper-teeth','tongue','upper-lip','lower-lip','hand-L-finger-0','hand-R-finger-0'):
            self.assertIn(id,ids)

if __name__=='__main__':unittest.main()