"""Optional separated-jaw head on the existing continuous-wrist body."""
from lingual_cartoon_scene import LingualCartoonSceneBody
from separated_cartoon_head import SeparatedCartoonHead
from cartoon_body import ROOT

class SeparatedCartoonSceneBody(LingualCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=SeparatedCartoonHead(root)
