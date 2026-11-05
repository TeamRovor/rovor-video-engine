"""Source-edge correspondence, preserving original generated paint and alpha.

Alpha thresholds locate the source contour for registration only. They never
clean, fill, replace or binarize source pixels. No timing or target changes.
"""
import cv2,numpy as np
from guided_jaw_exposure import SOURCE,TRI,smooth

KNOTS=np.array([164,181,194,211,228.5,246,263,278,298,329],np.float32)
GUIDE_TOP=np.array([315,320,325,327,328.5,327,325,323.285714,321,320],np.float32)

def source_mesh(jaw):
 alpha=jaw[:,:,3].astype('float32');rows=[];actual=[]
 for x,expected in zip(KNOTS,GUIDE_TOP):
  values=cv2.remap(alpha,np.full((512,1),x,np.float32),np.arange(512,dtype=np.float32)[:,None],cv2.INTER_LINEAR)[:,0]
  # Explicit expected source band avoids disconnected tiny-alpha RGB/dust.
  candidates=np.where((np.arange(512)>=expected-8)&(np.arange(512)<=expected+8)&(values>=127.5))[0]
  if not len(candidates):raise ValueError(f'No drawn jaw edge near source guide x{x}')
  y=int(candidates[0]);before=values[y-1];after=values[y]
  crossing=(y-1)+(127.5-before)/max(float(after-before),1e-6)
  actual.append(crossing);rows.append(dict(x=float(x),guideY=float(expected),paintedHalfAlphaY=float(crossing),sourceResidualY=float(crossing-expected)))
 source=SOURCE.copy();x,y=SOURCE.T
 delta=np.interp(x,KNOTS,np.asarray(actual)-GUIDE_TOP)
 # Correct only the lip-bearing source band, leaving outer face/chin art.
 side=smooth((x-164)/17)*smooth((298-x)/20);vertical=1-smooth((y-335)/40)
 source[:,1]+=delta*side*vertical
 t=source[TRI];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
 if area.min()<=0:raise ValueError('Inverted source correspondence mesh')
 return source,dict(knots=rows,minimumSourceTriangleArea2=float(area.min()),sourcePixelsModified=False,sourceAlphaModified=False,targetGeometryChanged=False,chinArtCorrected=False)

def corresponding_fields(source,target,scale=3):
 size=512*scale;mx=np.full((size,size),-1,np.float32);my=mx.copy()
 for ids in TRI:
  triangle=target[ids]*scale;x,y,w,h=cv2.boundingRect(triangle);x=max(0,x);y=max(0,y);w=min(size-x,w);h=min(size-y,h)
  if w<=0 or h<=0:continue
  inv=cv2.getAffineTransform(triangle,source[ids]);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32');mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(triangle-[x,y]).astype('int32'),255);take=mask>0
  mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take];my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
 return mx,my
