"""Same-timing isolated art comparison; does not promote a generated plate."""
import argparse,json
from pathlib import Path
import cv2
from render_contact_material_review import Review,START,END,FPS
from material_cartoon_head import MaterialCartoonHead
from sculpted_contact_head import SculptedContactHead
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=START);p.add_argument('--end',type=int,default=END);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[MaterialCartoonHead(),SculptedContactHead()],titles=['CURRENT: relaxed contact','CANDIDATE: separate lower-lip volume'],heading='“favicon” to pause · same audio/timing · new contact art')
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-START:06}.jpg',quality=97)
