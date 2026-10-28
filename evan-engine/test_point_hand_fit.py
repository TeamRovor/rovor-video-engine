"""Point registration and mesh guards; not anatomy or transition approval."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from finished_cartoon_scene import FinishedCartoonSceneBody
from relaxed_cartoon_scene import RelaxedWristArm
from payoff_cartoon_review import payoff_controls
from build_relaxed_cartoon_hand import build

class PointFitTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.folder=ROOT/'point-hand-fit-v1';cls.meta=json.loads((cls.folder/'manifest.json').read_text());cls.plan=json.loads((ROOT.parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_source_proximal_preservation_and_current_mesh(self):
  for name,digest in self.meta['sourceSha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
  old=np.array(Image.open(ROOT/'body-rig/arm-right.png').convert('RGBA'));new=np.array(Image.open(self.folder/'right-skin.png').convert('RGBA'));yy,xx=np.mgrid[:1536,:1024];axis=np.array(self.meta['axis']);s=(xx-810)*axis[0]+(yy-762)*axis[1];np.testing.assert_array_equal(old[s<=-36],new[s<=-36]);self.assertEqual(int(new[[0,-1],:,3].max()),0);self.assertEqual(int(new[:,[0,-1],3].max()),0)
  reference=FinishedCartoonSceneBody().arms['right'];arm=RelaxedWristArm(Image.fromarray(new),reference.geometry,reference);ids=np.array(arm.triangles)
  for t in np.arange(0,22.125,1/48):
   p=arm.posed_vertices(payoff_controls(t,self.plan)['right'])[ids];v=p[:,1:]-p[:,0,None];self.assertGreater(float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min()),0)
 def test_isolated_rebuild_matches_working_derivatives(self):
  with tempfile.TemporaryDirectory()as directory:
   root=Path(directory)
   for name in ['body-rig/arm-right.png','source/design-sheet-v1.png','hand-source/right-point-v1.png']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
   (root/'point-hand-fit-v1').mkdir()
   meta=build(root,folder_name='point-hand-fit-v1',source_name='../hand-source/right-point-v1.png',source_wrist=(457.,531.),source_scale=.192,source_antialias=True)
   self.assertEqual(meta,self.meta)
   for name in ['right-skin.png','registered-hand.png','blend-mask.png']:np.testing.assert_array_equal(np.array(Image.open(root/'point-hand-fit-v1'/name)),np.array(Image.open(self.folder/name)))

if __name__=='__main__':unittest.main()
