"""One registered relaxed hand pose on the existing independent arm/wrist.

No discrete pose changes, finger dissolve, or independent-digit claim.
"""
import numpy as np
from PIL import Image
from painted_character import arm_transforms,smooth
from cartoon_body import ROOT
from detail_cartoon_scene import DetailCartoonSceneBody
from joined_cartoon_wrist import JoinedWristArm
class RelaxedWristArm(JoinedWristArm):
 def posed_vertices(self,angles):
  v=np.c_[self.vertices,np.ones(len(self.vertices))];axis=np.array([61.,137.]);axis/=np.linalg.norm(axis)
  s=(self.vertices-np.array(self.geometry['wrist']))@axis
  # Wrist influence follows the actual forearm axis, so an open thumb that
  # projects sideways/backward is already rigidly parented to the hand.
  e=smooth((self.vertices[:,1]-self.geometry['elbow'][1]+55)/110)
  w=smooth((s+30)/60);weights=np.c_[1-e,e*(1-w),e*w]
  return sum((v@m.T)[:,:2]*weights[:,i:i+1] for i,m in enumerate(arm_transforms(self.geometry,angles)))

class RelaxedCartoonSceneBody(DetailCartoonSceneBody):
 def __init__(self,root=ROOT):
  super().__init__(root);old=self.arms['right'];self.arms['right']=RelaxedWristArm(Image.open(root/'relaxed-hand-v1/right-skin.png').convert('RGBA'),old.geometry,old)
 def layers(self,t,plan,controls=None):
  layers=super().layers(t,plan,controls);del layers['index-right'];return layers
