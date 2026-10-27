"""Registered-source and actual acting guards; not anatomy approval."""
import json,hashlib,unittest,tempfile,shutil
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from finished_cartoon_scene import FinishedCartoonSceneBody
from relaxed_cartoon_scene import RelaxedWristArm
from dismissive_cartoon_review import dismissive_controls
from painted_character import arm_transforms
from build_relaxed_cartoon_hand import build

class CleanPalmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.folder=ROOT/'open-palm-clean-v1';cls.meta=json.loads((cls.folder/'manifest.json').read_text());body=FinishedCartoonSceneBody();old=body.arms['right'];cls.arm=RelaxedWristArm(Image.open(cls.folder/'right-skin.png').convert('RGBA'),old.geometry,old);cls.plan=json.loads((ROOT.parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_proximal_art_source_hash_and_bounds(self):
  for name,digest in self.meta['sourceSha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
  a=np.array(Image.open(ROOT/'body-rig/arm-right.png').convert('RGBA'));b=np.array(Image.open(self.folder/'right-skin.png').convert('RGBA'));yy,xx=np.mgrid[:1536,:1024];o=np.array(self.meta['targetWrist']);axis=np.array(self.meta['axis']);s=(xx-o[0])*axis[0]+(yy-o[1])*axis[1];np.testing.assert_array_equal(a[s<=-36],b[s<=-36]);self.assertEqual(int(b[[0,-1],:,3].max()),0);self.assertEqual(int(b[:,[0,-1],3].max()),0)
 def test_current_speech_geometry_and_rigid_distal_parent(self):
  arm=self.arm;ids=np.array(arm.triangles)
  for t in np.arange(0,22.125,1/48):
   a=dismissive_controls(float(t),self.plan)['right'];p=arm.posed_vertices(a)[ids];v=p[:,1:]-p[:,0,None];self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)
  axis=np.array(self.meta['axis']);take=(arm.vertices-arm.geometry['wrist'])@axis>=30;v=arm.vertices[take];self.assertGreater(len(v),0)
  for a in [[-3,-38,-5],[-6,-30,-30]]:np.testing.assert_allclose(arm.posed_vertices(a)[take],(np.c_[v,np.ones(len(v))]@arm_transforms(arm.geometry,a)[2].T)[:,:2],atol=1e-6)
 def test_invalid_landmark_does_not_write_derivative(self):
  p=self.folder/'right-skin.png';before=p.read_bytes()
  for pivot in [(float('nan'),510),(551,),[551,510,0]]:
   with self.assertRaises(ValueError):build(folder_name='open-palm-clean-v1',source_name='source-v2.png',source_wrist=pivot)
  for scale in [0.,-1.,float('nan')]:
   with self.assertRaises(ValueError):build(folder_name='open-palm-clean-v1',source_name='source-v2.png',source_scale=scale)
  self.assertEqual(before,p.read_bytes())
 def test_default_build_stays_pixel_exact_in_isolated_copy(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   for name in ['relaxed-hand-v1/source/right-relaxed-v2.png','body-rig/arm-right.png','source/design-sheet-v1.png','hand-source/right-point-v1.png']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
   meta=build(root)
   for name in ['right-skin.png','registered-hand.png','blend-mask.png']:np.testing.assert_array_equal(np.array(Image.open(root/'relaxed-hand-v1'/name)),np.array(Image.open(ROOT/'relaxed-hand-v1'/name)))
   self.assertEqual(meta,json.loads((ROOT/'relaxed-hand-v1/manifest.json').read_text()))
 def test_distal_proportions_match_opposite_hand(self):
  measurements=[]
  for p,wrist,elbow in [(ROOT/'body-rig/arm-left.png',[214,762],[275,625]),(self.folder/'right-skin.png',[810,762],[749,625])]:
   a=np.array(Image.open(p));y,x=np.where(a[:,:,3]>127);v=np.c_[x,y]-wrist;axis=np.array(wrist)-elbow;axis=axis/np.linalg.norm(axis);s=v@axis;q=v@[-axis[1],axis[0]];measurements.append([s[s>=0].max(),np.ptp(q[s>=0])])
  ratio=np.array(measurements[1])/measurements[0]
  self.assertTrue(np.all((ratio>.95)&(ratio<1.05)),ratio)

if __name__=='__main__':unittest.main()
