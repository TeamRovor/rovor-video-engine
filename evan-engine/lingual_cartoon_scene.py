"""Opt-in tongue study on the continuous-wrist cartoon body."""
from joined_cartoon_wrist import JoinedWristSceneBody
from lingual_cartoon_head import LingualCartoonHead
from cartoon_body import ROOT

class LingualCartoonSceneBody(JoinedWristSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.head=LingualCartoonHead(root)
