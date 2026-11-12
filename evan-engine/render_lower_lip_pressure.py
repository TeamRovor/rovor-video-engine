"""Authored isolated pressure/release test, explicitly not a speech profile."""
import argparse,json,cv2,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw
from labiodental_construction import LabiodentalConstruction,load
from lower_lip_plane import LowerLipPlane
from lip_surface_correspondence import source_mesh
from layered_cartoon_head import over,straight
from cartoon_body import ROOT
from render_cartoon_head_study import font

def assemble(rig,lip,release,pressure):
 rig.pose(release);source=rig.last_parts;arch=rig.last_oral[:9][::-1].copy()
 # The authored outer arch includes1.1px of ink margin above its inner edge.
 arch[:,1]-=1.1*np.sin(np.arange(8,-1,-1)*np.pi/8)
 lower=lip.pose(arch,pressure);skin=np.zeros_like(rig.face);skin[305:365,190:285]=rig.face[305:365,190:285]
 parts={'Neck backing':source['Neck backing'],'Drawn face skin underlap':skin,'Painted cavity':source['Painted cavity'],'Fixed upper incisors':source['Fixed upper incisors'],'Drawn jaw skin':source['Drawn jaw and lower lip'],'Independent lower lip':lower,'Drawn upper-lip cap':source['Drawn upper-lip cap'],'Upper face and cheek wings':source['Upper face and cheek wings']}
 result=np.zeros_like(lower)
 for part in parts.values():result=over(result,part)
 return Image.fromarray(np.rint(np.clip(straight(result),0,255)).astype('uint8')),parts

def ease(t):
 t=float(np.clip(t,0,1));return t*t*t*(10+t*(-15+6*t))

if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);(a.output/'frames').mkdir(exist_ok=True)
 rig=LabiodentalConstruction();rig.jaw=load(ROOT/'jaw-simplification-v1/Jaw-Candidate.png');rig.source_points,_=source_mesh(rig.jaw);lip=LowerLipPlane();rows=[]
 for i in range(48):
  release=0 if i<24 else ease((i-24)/15) if i<40 else 1-ease((i-40)/7)
  pressure=ease(i/15) if i<16 else 1 if i<24 else 1-ease((i-24)/7) if i<32 else 0
  old,old_parts=assemble(rig,lip,release,0);new,parts=assemble(rig,lip,release,pressure)
  for name in parts:
   if name!='Independent lower lip':np.testing.assert_array_equal(old_parts[name],parts[name])
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((25,20),'INDEPENDENT LOWER LIP / eight actual painted planes',font=font(26),fill='#253c49');d.text((35,65),'Pressure locked at0 / same jaw',font=font(22),fill='#48636d');d.text((685,65),'Authored pressure before jaw release',font=font(22),fill='#48636d');im.paste(old,(55,95),old);im.paste(new,(700,95),new)
  d.text((35,625),f'Silent component study / frame{i} / jaw release {release:.3f} / independent pressure {pressure:.3f}',font=font(21),fill='#253c49');d.text((35,674),'Actual lip paint; not narration alignment, accepted contact anatomy or finished acting.',font=font(21),fill='#48636d');im.save(a.output/'frames'/f'{i:06}.png')
  if i in [0,8,15,23,28,31,39,47]:new.save(a.output/f'Native-{i:02}.png')
  rows.append(dict(frame=i,release=release,pressure=pressure,allOtherPlanesPairExact=True,lowerLipAlphaArea=float(parts['Independent lower lip'][:,:,3].sum()/255),planes=list(parts)))
  if i%12==0:print(i,flush=True)
 (a.output/'Animation-Audit.json').write_text(json.dumps(dict(frames=48,fps=48,silentAuthoredCycle=True,speechProfile=False,sourcePixelsChanged=False,alphaCleanup=False,anatomyAccepted=False,rows=rows),indent=2)+'\n')
