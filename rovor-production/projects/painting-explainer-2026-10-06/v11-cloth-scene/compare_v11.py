"""Review frames and movement from *decoded videos*, not original source art.

Comparison is evidence of changed frames, not an aesthetic certification.
"""
import argparse,io,subprocess,json
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from pathlib import Path
TIMES=[.4,1.65,3.05,4.65,5.65]
def frame(file,sec):
 b=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-ss',str(sec),'-i',str(file),'-frames:v','1','-f','image2pipe','-vcodec','mjpeg','pipe:1'])
 return Image.open(io.BytesIO(b)).convert('RGB')
def run(old,new,source_start,view,outimg,outjson):
 # One row for old original source frame, one for edited insert, in each orientation.
 w,h=(420,236) if view=='landscape' else (235,420)
 im=Image.new('RGB',(w*len(TIMES),h*2+28*2),'white');d=ImageDraw.Draw(im)
 allpairs=[];small=[]
 for ix,t in enumerate(TIMES):
  pair=[]
  for row,p,time in [(0,old,source_start+t),(1,new,t)]:
   fr=frame(p,time);fr.thumbnail((w,h));x=ix*w+(w-fr.width)//2;y=row*(h+28)+(h-fr.height)//2
   im.paste(fr,(x,y));d.text((ix*w+4,row*(h+28)+h+3),f'{"PREVIOUS" if row==0 else "V11 STUDY"}  {t:.2f}s',fill='#242424')
   pair.append(np.asarray(fr.resize((240,135))).astype('int16'))
  allpairs.append(float(np.mean(np.abs(pair[0]-pair[1]))))
 for path,offset in [(old,source_start),(new,0)]:
  imgs=[np.asarray(frame(path,offset+t).resize((180,101)),dtype='int16') for t in TIMES]
  small.append([float(np.mean(np.abs(b-a))) for a,b in zip(imgs,imgs[1:])])
 im.save(outimg,quality=88)
 result=dict(orientation=view,comparisonSeconds=TIMES,oldMotionIntervals=small[0],newMotionIntervals=small[1],meanOldMotion=float(np.mean(small[0])),meanNewMotion=float(np.mean(small[1])),oldNewFrameDelta=allpairs,imagesAreDecodedFromPlayableMP4=True,artisticApproval=False)
 Path(outjson).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--old',required=True);p.add_argument('--new',required=True);p.add_argument('--source-start',type=float,default=108);p.add_argument('--view',required=True);p.add_argument('--img',required=True);p.add_argument('--report',required=True);a=p.parse_args()
 run(a.old,a.new,a.source_start,a.view,a.img,a.report)