"""Same word-anchored acting, opt-in shorter/shallow resting index."""
from cartoon_scene import CartoonMaterialSceneBody,scene_controls
from cartoon_body import ROOT
from compact_cartoon_index import CompactIndexRig

def compact_controls(t,plan):
    controls=scene_controls(t,plan)
    controls['index']=[v*.7 for v in controls['index']]
    return controls

class CompactCartoonSceneBody(CartoonMaterialSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.index_rig=CompactIndexRig(root)
    def layers(self,t,plan,controls=None):
        return super().layers(t,plan,compact_controls(t,plan) if controls is None else controls)
    def render(self,t,plan,controls=None):
        return super().render(t,plan,compact_controls(t,plan) if controls is None else controls)
