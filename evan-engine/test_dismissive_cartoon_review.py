import copy,json,unittest
from pathlib import Path
import cv2,numpy as np
from dismissive_cartoon_review import dismissive_controls
from definition_cartoon_review import definition_controls
from finished_cartoon_scene import FinishedCartoonSceneBody

class DismissiveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_isolation_fallback_and_shift(self):
  before=copy.deepcopy(self.plan)
  for t in [0,5.14,7.45,11.5,23]:self.assertEqual(dismissive_controls(t,self.plan),definition_controls(t,self.plan))
  for t in np.linspace(5,7.5,100):
   a,b=dismissive_controls(t,self.plan),definition_controls(t,self.plan)
   for key in set(a)-{'left'}:self.assertEqual(a[key],b[key])
  p=copy.deepcopy(self.plan);p['words'][20]['word']='other';self.assertEqual(dismissive_controls(6,p),definition_controls(6,p))
  p=copy.deepcopy(self.plan)
  for w in p['words']:w['start']+=3;w['end']+=3
  a=np.array(dismissive_controls(6,self.plan)['left'])-definition_controls(6,self.plan)['left'];b=np.array(dismissive_controls(9,p)['left'])-definition_controls(9,p)['left'];np.testing.assert_allclose(a,b)
  self.assertEqual(before,self.plan)
 def test_actual_arm_continuity_and_invalid_cues(self):
  arm=FinishedCartoonSceneBody().arms['left'];tri=np.array(arm.triangles);angles=[]
  for t in np.arange(5,7.5,1/480):
   a=dismissive_controls(float(t),self.plan)['left'];angles.append(a);p=arm.posed_vertices(a)[tri];v=p[:,1:]-p[:,0,None];self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)
  self.assertLess(float(abs(np.diff(angles,axis=0)).max()),.6)
  for t in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):dismissive_controls(t,self.plan)
  p=copy.deepcopy(self.plan);p['words'][21]['end']=0
  with self.assertRaises(ValueError):dismissive_controls(6,p)

if __name__=='__main__':unittest.main()
