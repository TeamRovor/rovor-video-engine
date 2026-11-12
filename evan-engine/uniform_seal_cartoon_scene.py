"""Optional bilabial-only seal on the current official-brand staging."""
from independent_chin_cartoon_scene import IndependentChinCartoonSceneBody
from uniform_seal_cartoon_head import UniformSealCartoonHead
from cartoon_body import ROOT
class UniformSealCartoonSceneBody(IndependentChinCartoonSceneBody):
 def __init__(self,root=ROOT):
  super().__init__(root);self.head=UniformSealCartoonHead(root)
