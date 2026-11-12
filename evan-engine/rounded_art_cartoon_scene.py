"""Optional rounded-art component study on the current articulated body."""
from bounded_cartoon_scene import BoundedCartoonSceneBody
from rounded_art_cartoon_head import RoundedArtCartoonHead
from cartoon_body import ROOT

class RoundedArtCartoonSceneBody(BoundedCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=RoundedArtCartoonHead(root)
