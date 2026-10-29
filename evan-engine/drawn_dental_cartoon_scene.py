"""Optional broad dental source drawing on existing narration-driven staging."""
from rooted_floor_cartoon_scene import RootedFloorCartoonSceneBody
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
from cartoon_body import ROOT
class DrawnDentalCartoonSceneBody(RootedFloorCartoonSceneBody):
 def __init__(self,root=ROOT):
  super().__init__(root);self.head=DrawnDentalCartoonHead(root)
