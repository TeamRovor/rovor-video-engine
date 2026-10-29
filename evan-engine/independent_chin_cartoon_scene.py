"""Optional independent chin anchors on current narrated/official-brand stage."""
from drawn_dental_cartoon_scene import DrawnDentalCartoonSceneBody
from independent_chin_cartoon_head import IndependentChinCartoonHead
from cartoon_body import ROOT
class IndependentChinCartoonSceneBody(DrawnDentalCartoonSceneBody):
 def __init__(self,root=ROOT):
  super().__init__(root);self.head=IndependentChinCartoonHead(root)
