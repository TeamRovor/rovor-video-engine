"""Optional broad oral artwork on the existing layered cartoon body."""
from light_lip_cartoon_scene import LightLipCartoonSceneBody
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from cartoon_body import ROOT
class BroadCavityCartoonSceneBody(LightLipCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=BroadCavityCartoonHead(root)
