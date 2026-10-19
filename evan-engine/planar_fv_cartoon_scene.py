"""Optional two-layer planar contact on the current character body."""
from occluded_teeth_cartoon_scene import OccludedTeethCartoonSceneBody
from planar_fv_cartoon_head import PlanarFVCartoonHead
from cartoon_body import ROOT
class PlanarFVCartoonSceneBody(OccludedTeethCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=PlanarFVCartoonHead(root)
