"""Optional short-AO height budget on existing narration-driven branding."""
from independent_chin_cartoon_scene import IndependentChinCartoonSceneBody
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
from cartoon_body import ROOT
class RoundedDurationCartoonSceneBody(IndependentChinCartoonSceneBody):
 def __init__(self,root=ROOT):
  super().__init__(root);self.head=RoundedDurationCartoonHead(root)
