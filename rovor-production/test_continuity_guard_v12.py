import unittest,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from continuity_guard_v12 import audit_positions,audit_contact
from estimate_desk_v12 import frame,FPS
class Tests(unittest.TestCase):
 def test_nominal_positions(self):self.assertTrue(audit_positions([(i,i*.33, 9+i*.1) for i in range(90)])['valid'])
 def test_teleport(self):self.assertFalse(audit_positions([(0,0,0),(1,200,0)])['valid'])
 def test_gap(self):self.assertFalse(audit_positions([(0,0,0),(2,1,0)])['valid'])
 def test_no_samples(self):self.assertFalse(audit_positions([])['valid'])
 def test_contact(self):self.assertTrue(audit_contact([(4,(10,10),(20,16)),(5,(11,12),(20,19))])['valid'])
 def test_detached(self):self.assertFalse(audit_contact([(1,(0,0),(90,60))])['valid'])
 def test_real_desk_stamp_motion(self):
  # Physically generated artwork track in both compositions: no old teleport.
  for view in ('landscape','portrait'):
   arr=[]
   for i in range(int(5.25*FPS),int(10.20*FPS)):
    svg=frame(i/FPS,view)
    m=re.search(r'<g transform="translate\(([0-9.]+) ([0-9.]+)\) rotate\(-7.00\)"',svg)
    self.assertIsNotNone(m,(view,i))
    arr.append((i,float(m.group(1)),float(m.group(2))))
   report=audit_positions(arr,max_pixels_per_frame=12)
   self.assertTrue(report['valid'],report)
if __name__=='__main__': unittest.main()