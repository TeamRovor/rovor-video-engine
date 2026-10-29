"""Optional shared F/V oral contour on the current articulated cartoon body."""
from planar_fv_cartoon_scene import PlanarFVCartoonSceneBody
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from cartoon_body import ROOT
class CorrespondentFVCartoonSceneBody(PlanarFVCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=CorrespondentFVCartoonHead(root)
