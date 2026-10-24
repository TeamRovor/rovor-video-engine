"""Ablate only upper teeth at one frame; not a proposed tooth-free design."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from render_lingual_review import Review

class WithoutUpperTeeth(BroadCavityCartoonHead):
    def clip_interiors(self,teeth,tongue,interior,w,shape_weights=None):
        teeth,tongue=super().clip_interiors(teeth,tongue,interior,w,shape_weights)
        return np.zeros_like(teeth),tongue

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);p.add_argument('--frame',type=int,default=148);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[BroadCavityCartoonHead(),WithoutUpperTeeth()],titles=['CANDIDATE: current upper teeth','DIAGNOSTIC: upper teeth removed'],heading='Layer diagnosis only · right panel is not a proposed design',start=120,end=240)
    a.output.parent.mkdir(parents=True,exist_ok=True);review.frame(a.frame).save(a.output,quality=98)
