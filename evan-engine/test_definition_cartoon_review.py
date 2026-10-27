import copy,json,unittest
from pathlib import Path
import cv2,numpy as np
from definition_cartoon_review import definition_event,definition_controls
from finished_cartoon_scene import finished_controls,FinishedCartoonSceneBody
class DefinitionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_exact_phrase_and_shifted_anchors(self):
  event=definition_event(self.plan);self.assertEqual(event['scriptIndices'],list(range(30,43)))
  p=copy.deepcopy(self.plan)
  for w in p['words']:w['start']+=3;w['end']+=3
  for key in ['anticipate','arrive','hold','settle']:self.assertAlmostEqual(definition_event(p)[key],event[key]+3)
  p['words'][34]['word']='other';self.assertIsNone(definition_event(p));self.assertEqual(definition_controls(11,p),finished_controls(11,p))
 def test_isolation_exact_off_hold_and_plan_immutability(self):
  before=copy.deepcopy(self.plan);e=definition_event(self.plan)
  for t in [0,e['anticipate'],e['settle'],20,23]:self.assertEqual(definition_controls(t,self.plan),finished_controls(t,self.plan))
  self.assertEqual(definition_controls(11.5,self.plan)['right'],[-3.,-38.,-5.])
  for t in np.linspace(0,23,100):
   a,b=definition_controls(t,self.plan),finished_controls(t,self.plan)
   for key in set(a)-{'right'}:self.assertEqual(a[key],b[key])
  self.assertEqual(before,self.plan)
 def test_continuity_actual_arm_geometry_and_invalid_cues(self):
  arm=FinishedCartoonSceneBody().arms['right'];tri=np.array(arm.triangles);angles=[]
  for t in np.arange(9.5,14.8,1/480):
   a=definition_controls(float(t),self.plan)['right'];angles.append(a)
   p=arm.posed_vertices(a)[tri];v=p[:,1:]-p[:,0,None];self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)
  self.assertLess(float(abs(np.diff(angles,axis=0)).max()),.3)
  for t in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):definition_controls(t,self.plan)
  p=copy.deepcopy(self.plan);p['words'][42]['end']=0
  with self.assertRaises(ValueError):definition_event(p)
if __name__=='__main__':unittest.main()
