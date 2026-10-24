"""Registration, hierarchy and silhouette safeguards, not art approval."""
import json,unittest
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from painted_character import arm_transforms
from detail_cartoon_scene import detail_controls
from relaxed_cartoon_scene import RelaxedCartoonSceneBody
class RelaxedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.body=RelaxedCartoonSceneBody();cls.meta=json.loads((ROOT/'relaxed-hand-v1/manifest.json').read_text());cls.plan=json.loads((ROOT.parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').resolve().read_text())
 def test_proximal_source_exact_and_canvas_not_clipped(self):
  original=np.array(Image.open(ROOT/'body-rig/arm-right.png').convert('RGBA'));joined=np.array(Image.open(ROOT/'relaxed-hand-v1/right-skin.png').convert('RGBA'));yy,xx=np.mgrid[:1536,:1024];o=np.array(self.meta['targetWrist']);axis=np.array(self.meta['axis']);s=(xx-o[0])*axis[0]+(yy-o[1])*axis[1];np.testing.assert_array_equal(joined[s<=-36],original[s<=-36]);self.assertEqual(int(joined[[0,-1],:,3].max()),0);self.assertEqual(int(joined[:,[0,-1],3].max()),0)
 def test_new_pose_mesh_positive_through_real_acting(self):
  arm=self.body.arms['right'];ids=np.array(arm.triangles)
  for i in range(1059):
   v=arm.posed_vertices(detail_controls(i/48,self.plan)['right']);t=v[ids];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)
 def test_distal_hand_has_same_wrist_parent(self):
  arm=self.body.arms['right'];axis=np.array([61.,137.]);axis/=np.linalg.norm(axis);take=(arm.vertices-np.array(arm.geometry['wrist']))@axis>=30;vertices=arm.vertices[take];self.assertGreater(len(vertices),0)
  for angles in [[-2,0,0],[-6,-30,-30]]:
   actual=arm.posed_vertices(angles)[take];expected=(np.c_[vertices,np.ones(len(vertices))]@arm_transforms(arm.geometry,angles)[2].T)[:,:2];np.testing.assert_allclose(actual,expected,atol=1e-6)
 def test_old_index_not_composited(self):
  layers=self.body.layers(748/48,self.plan);self.assertNotIn('index-right',layers);self.assertNotIn('palm-right',layers);self.assertIn('arm-right',layers)
if __name__=='__main__':unittest.main()
