import copy,json,unittest
from pathlib import Path
import numpy as np
from payoff_cartoon_review import payoff_controls
from dismissive_cartoon_review import dismissive_controls
from detail_cartoon_scene import detail_event

class PayoffTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_shared_cue_isolation_shift_and_immutability(self):
  before=copy.deepcopy(self.plan);e=detail_event(self.plan)
  for t in [0,11,14.3,e['settle']+.07,20,23]:self.assertEqual(payoff_controls(t,self.plan),dismissive_controls(t,self.plan))
  for t in np.arange(14.3,17,1/48):
   a,b=payoff_controls(t,self.plan),dismissive_controls(t,self.plan)
   for k in set(a)-{'head','body_roll'}:self.assertEqual(a[k],b[k])
  a,b=payoff_controls(15.6,self.plan),dismissive_controls(15.6,self.plan)
  self.assertAlmostEqual(a['head']-b['head'],-3.2);self.assertAlmostEqual(a['body_roll']-b['body_roll'],.85)
  p=copy.deepcopy(self.plan)
  for w in p['words']:w['start']+=3;w['end']+=3
  for k in ['head','body_roll']:self.assertAlmostEqual(payoff_controls(18.6,p)[k],a[k])
  p['words'][44]['word']='different';self.assertEqual(payoff_controls(18.6,p),dismissive_controls(18.6,p));self.assertEqual(self.plan,before)
 def test_continuity_and_invalid_time(self):
  rows=[[payoff_controls(t,self.plan)[k] for k in ['head','body_roll']] for t in np.arange(14.3,17,1/480)]
  self.assertLess(float(abs(np.diff(rows,axis=0)).max()),.04)
  for t in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):payoff_controls(t,self.plan)
 def test_actual_neck_mesh_with_current_jaw_trajectory(self):
  from finished_cartoon_scene import FinishedCartoonSceneBody
  from cartoon_neck import neck_vertices,TRIANGLES
  from cartoon_head import SYMBOLS
  from speech_planner import planned_weights
  geometry=FinishedCartoonSceneBody().head.geometry
  for t in np.arange(14.3,17,1/480):
   weights=planned_weights(t,self.plan,self.plan['fallbackCues'])
   delta=sum(float(w)*(geometry[s][8]-393) for s,w in zip(SYMBOLS,weights))
   _,vertices=neck_vertices(payoff_controls(t,self.plan)['head'],delta,(195,355),.25)
   p=vertices[np.asarray(TRIANGLES)];v=p[:,1:]-p[:,0,None]
   self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)

if __name__=='__main__':unittest.main()
