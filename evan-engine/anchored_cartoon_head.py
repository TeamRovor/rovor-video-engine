"""Opt-in stable cheek paint under independent oral layers and moving jaw."""
from separated_cartoon_head import SeparatedCartoonHead
from cartoon_head import POINTS

class AnchoredCartoonHead(SeparatedCartoonHead):
    def skin_target(self,weights,target):
        skin=super().skin_target(weights,target)
        # Oral art has its own mesh. Moving this skin ring with a narrow vowel
        # pulled sideburn/ear ink across the cheek. Retain the source skin ring
        # while leaving all external anchors (including chin/jaw) articulated.
        skin[:32]=POINTS['X'][:32]
        return skin
