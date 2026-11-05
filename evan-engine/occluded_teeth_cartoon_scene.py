"""Optional tooth occlusion study on the current layered character body."""
from broad_cavity_cartoon_scene import BroadCavityCartoonSceneBody
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead
from cartoon_body import ROOT
class OccludedTeethCartoonSceneBody(BroadCavityCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=OccludedTeethCartoonHead(root)
