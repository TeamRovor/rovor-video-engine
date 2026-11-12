"""Anchored facial skin on the existing articulated continuous-wrist body."""
from separated_cartoon_scene import SeparatedCartoonSceneBody
from anchored_cartoon_head import AnchoredCartoonHead
from cartoon_body import ROOT

class AnchoredCartoonSceneBody(SeparatedCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=AnchoredCartoonHead(root)
