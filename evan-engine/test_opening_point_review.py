import copy,json,unittest
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from opening_point_review import opening_point_event,opening_point_controls,opening_point_pose,pointing_ray,POINT_TARGET
from payoff_cartoon_review import payoff_controls
from finished_cartoon_scene import FinishedCartoonSceneBody
from relaxed_cartoon_scene import RelaxedWristArm

class OpeningPointTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plan=json.loads((ROOT.parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_phrase_shift_fallback_and_isolation(self):
  p=copy.deepcopy(self.plan);e=opening_point_event(p);self.assertEqual(e['scriptIndices'],list(range(8,18)))
  for t in [0,e['anticipate'],e['settle'],11.17,15.6,23]:self.assertEqual(opening_point_controls(t,p),payoff_controls(t,p));self.assertEqual(opening_point_pose(t,p),'open')
  for t in [2.2,2.5,3.3,4.9]:
   a,b=opening_point_controls(t,p),payoff_controls(t,p)
   for k in set(a)-{'right'}:self.assertEqual(a[k],b[k])
   self.assertEqual(a['right'][:2],b['right'][:2])
  self.assertEqual(p,self.plan)
  for w in p['words']:w['start']+=2;w['end']+=2
  for key in ['anticipate','arrive','hold','settle','poseOn','poseOff']:self.assertAlmostEqual(opening_point_event(p)[key],e[key]+2)
  p['words'][10]['word']='different';self.assertIsNone(opening_point_event(p));self.assertEqual(opening_point_controls(3,p),payoff_controls(3,p));self.assertEqual(opening_point_pose(3,p),'open')
 def test_held_authored_ray_and_discrete_pose_boundaries(self):
  for t in np.linspace(2.84,3.99,24):
   a,b=pointing_ray(opening_point_controls(t,self.plan));d=b-a;v=POINT_TARGET-a
   self.assertLess(abs(d[0]*v[1]-d[1]*v[0])/np.linalg.norm(d),.001);self.assertGreater(float(np.dot(d,POINT_TARGET-b)),0)
  e=opening_point_event(self.plan)
  for t,pose in [(e['poseOn']-1e-6,'open'),(e['poseOn'],'point'),(e['poseOff']-1e-6,'point'),(e['poseOff'],'open')]:self.assertEqual(opening_point_pose(t,self.plan),pose)
 def test_continuous_actual_meshes_and_invalid_time(self):
  reference=FinishedCartoonSceneBody().arms['right'];arms=[RelaxedWristArm(Image.open(ROOT/folder/'right-skin.png').convert('RGBA'),reference.geometry,reference)for folder in ['open-palm-filtered-v1','point-hand-fit-v1']];angles=[]
  for t in np.arange(1.6,5.4,1/480):
   c=opening_point_controls(float(t),self.plan);angles.append(c['right'])
   for arm in arms:
    p=arm.posed_vertices(c['right'])[np.array(arm.triangles)];v=p[:,1:]-p[:,0,None];self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)
  self.assertLess(float(abs(np.diff(angles,axis=0)).max()),.3)
  for t in [float('nan'),float('inf')]:
   for f in [opening_point_controls,opening_point_pose]:
    with self.assertRaises(ValueError):f(t,self.plan)

if __name__=='__main__':unittest.main()
