"""Optional lighter rounded oral artwork on the current articulated body."""
from contour_cartoon_scene import ContourCartoonSceneBody
from light_lip_cartoon_head import LightLipCartoonHead
from cartoon_body import ROOT

class LightLipCartoonSceneBody(ContourCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=LightLipCartoonHead(root)
