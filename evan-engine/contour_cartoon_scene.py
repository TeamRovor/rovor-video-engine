"""Optional contour correspondence on the current layered cartoon body."""
from rounded_art_cartoon_scene import RoundedArtCartoonSceneBody
from contour_cartoon_head import ContourCartoonHead
from cartoon_body import ROOT

class ContourCartoonSceneBody(RoundedArtCartoonSceneBody):
    def __init__(self, root=ROOT):
        super().__init__(root)
        self.head = ContourCartoonHead(root)
