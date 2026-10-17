"""Hand morph safety and actual continuity checks across every directed pose."""
import unittest, math, xml.etree.ElementTree as ET
from cartoon_hand_deform import finger_landmarks,render_hand,POSES

class HandDeformTests(unittest.TestCase):
    def test_all_hand_contacts_expose_independent_parts(self):
        for pose in POSES:
            root=ET.fromstring('<svg>'+render_hand([(pose,1)],prefix='R-')+'</svg>')
            ids={e.attrib['id']:e for e in root.iter() if 'id' in e.attrib}
            self.assertIn('R-thumb',ids)
            self.assertIn('R-hand-palm',ids)
            self.assertEqual(sum(k.startswith('R-finger-') for k in ids),4)
    def test_shared_topology_continuous_landmarks(self):
        for a,b in [('relaxed','open'),('open','point'),('point','fist'),('fist','explain')]:
            old=None
            for i in range(101):
                p=finger_landmarks([(a,1-i/100),(b,i/100)])
                points=[coord for finger in p['fingers'] for vertex in finger for coord in vertex]
                self.assertTrue(all(math.isfinite(x) for x in points))
                if old:
                    self.assertLess(max(abs(x-y) for x,y in zip(points,old)),2)
                old=points
    def test_invalid_weights_and_poses_rejected(self):
        for data in ([], [('bad',1)], [('open',-1)], [('open',float('nan'))], [('open',0)]):
            with self.assertRaises(ValueError):render_hand(data)

if __name__=='__main__':unittest.main()