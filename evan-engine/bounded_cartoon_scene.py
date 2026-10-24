"""Bounded head compositing on the existing articulated cartoon body."""
from anchored_cartoon_scene import AnchoredCartoonSceneBody
from bounded_cartoon_head import BoundedCartoonHead
from cartoon_body import ROOT

class BoundedCartoonSceneBody(AnchoredCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=BoundedCartoonHead(root)
