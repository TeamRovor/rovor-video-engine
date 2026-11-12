"""Optional duration-sensitive jaw and independent contact teeth in Rovor scene."""
from correspondent_fv_cartoon_scene import CorrespondentFVCartoonSceneBody
from duration_cartoon_head import DurationCartoonHead
from cartoon_body import ROOT
class DurationCartoonSceneBody(CorrespondentFVCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=DurationCartoonHead(root)
