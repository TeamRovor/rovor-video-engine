"""Optional phone-specific tongue on the existing staged reference."""
from rooted_floor_cartoon_scene import RootedFloorCartoonSceneBody
from phone_tongue_cartoon_head import PhoneTongueCartoonHead
from cartoon_body import ROOT
class PhoneTongueCartoonSceneBody(RootedFloorCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=PhoneTongueCartoonHead(root)
