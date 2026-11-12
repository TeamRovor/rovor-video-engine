"""Optional registered skin underpainting; existing oral artwork/timing retained."""
from PIL import Image
import numpy as np
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
from cartoon_body import ROOT
class ConstructionSkinCartoonHead(RoundedDurationCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.layers['face-skin']=np.array(Image.open(root/'construction-skin-v1/working-face-skin.png').convert('RGBA'))
