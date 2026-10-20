"""Optional retracted vowel blade / foreground floor on current Rovor staging."""
from duration_cartoon_scene import DurationCartoonSceneBody
from rooted_floor_cartoon_head import RootedFloorCartoonHead
from cartoon_body import ROOT
class RootedFloorCartoonSceneBody(DurationCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=RootedFloorCartoonHead(root)
