"""Review-only source-jaw exposure test, not a runtime head profile.

Painted jaw/lower lip are one source plane. Lip edge follows existing oral
controls; chin follows existing independent skin anchors. The cut carrier is a
placeholder: missing complementary cheek/neck art must remain visible.
"""
import cv2,numpy as np
from PIL import Image
from pathlib import Path
from maxillary_cartoon_head import MaxillaryCartoonHead
from layered_cartoon_head import over,straight
from cartoon_body import ROOT

X=np.array([128,145,164,181,194,211,228.5,246,263,298,329,355,384],np.float32)
Y=np.array([288,305,315,325,328.5,335,345,360,375,394,410,435,448],np.float32)
SOURCE=np.array([(x,y) for y in Y for x in X],np.float32)
TRI=[]
for j in range(len(Y)-1):
 for i in range(len(X)-1):
  a=j*len(X)+i;b=a+1;c=a+len(X);d=c+1;TRI.extend([[a,b,d],[a,d,c]])
TRI=np.asarray(TRI)
POLYGON=np.array([(164,315),(181,320),(194,325),(211,327),(228.5,328.5),(246,327),(263,325),(298,321),(329,320),(328,355),(304,360),(278,372),(245,389),(220,394),(195,391),(181,375),(164,335)],np.float32)

def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)

def target_mesh(oral,skin):
 target=SOURCE.copy();x,y=SOURCE.T
 horizontal=smooth((x-164)/30)*smooth((329-x)/66)
 center=(oral[8]+oral[0])/2;span=oral[0,0]-oral[8,0]
 upper=1-smooth((y-335)/59)
 target[:,0]+=(center[0]-228.5+(x-228.5)*(span/69-1))*horizontal*upper
 u=np.clip((x-194)/69,0,1);corner=(oral[8,1]-325)*(1-u)+(oral[0,1]-325)*u
 distance=np.minimum(abs(x-228.5)/34.5,1)
 # Rounded crest has zero center slope; a linear tent created an unintended
 # V-shaped lip edge when this drawn jaw opened. Same center/corner targets.
 mid=np.cos(distance*np.pi/2)
 lip_delta=corner+(oral[20,1]-328.5-(center[1]-325))*mid
 chin_delta=skin[46,1]-394
 target[:,1]+=lip_delta*horizontal*upper+chin_delta*(1-upper)
 return checked_mesh(target)

def checked_mesh(target):
 triangles=target[TRI];a=triangles[:,1]-triangles[:,0];b=triangles[:,2]-triangles[:,0];areas=a[:,0]*b[:,1]-a[:,1]*b[:,0]
 if not np.isfinite(target).all() or areas.min()<=0:raise ValueError(f'Invalid jaw mesh: {areas.min()}')
 return target,float(areas.min())

def contour_target_mesh(oral,skin):
 """Review-only lower-edge correspondence using all nine oral arch points.

 Unlike the legacy center/corner reconstruction, intermediate curve controls
 survive. No release normalization, temporal filtering or two-pose clipping.
 """
 arch=np.asarray(oral[:9][::-1],dtype=np.float32)
 if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Lower oral arch must be finite and ordered left to right')
 target,_=target_mesh(oral,skin);target[:,0]=SOURCE[:,0];x,y=SOURCE.T
 # Lip rounding belongs to the lip planes, not the jaw silhouette.
 horizontal=smooth((x-164)/30)*smooth((329-x)/66)
 # Linear depth falloff preserves ordering under deep openings; cubic can fold.
 upper=1-np.clip((y-335)/59,0,1)
 guide=np.interp(x,POLYGON[:11,0],POLYGON[:11,1])
 edge=np.interp(target[:,0],arch[:,0],arch[:,1])
 target[:,1]=y+(edge-guide)*horizontal*upper+(skin[46,1]-394)*(1-upper)
 return checked_mesh(target)


def fields(target,scale=3):
 size=512*scale;mx=np.full((size,size),-1,np.float32);my=mx.copy()
 for ids in TRI:
  triangle=target[ids]*scale;x,y,w,h=cv2.boundingRect(triangle);x=max(0,x);y=max(0,y);w=min(size-x,w);h=min(size-y,h)
  if w<=0 or h<=0:continue
  inv=cv2.getAffineTransform(triangle,SOURCE[ids]);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32');mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(triangle-[x,y]).astype('int32'),255);take=mask>0
  mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take];my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
 return mx,my


class CaptureHead(MaxillaryCartoonHead):
 def skin_target(self,weights,target):
  skin=super().skin_target(weights,target);self.exposure_skin=skin.copy();return skin


class GuidedJawExposure:
 def __init__(self):
  self.head=CaptureHead();raw=np.array(Image.open(ROOT/'guided-jaw-v1/Registered-Jaw-v2.png').convert('RGBA'));self.source=raw.astype('float32');self.source[:,:,:3]*=self.source[:,:,3:4]/255
  mask=np.zeros((1536,1536),np.uint8);cv2.fillPoly(mask,[np.rint(POLYGON*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8);self.cut=cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255
 def at(self,t,plan):
  reference=self.head.at(t,plan)
  if self.head.painted_rim is None:raise ValueError('No full F/V jaw assembly: this exposure cannot reuse a stale painted oral target')
  oral=self.head.last_painted_target
  target,minimum=target_mesh(oral,self.head.exposure_skin);maps=fields(target)
  part=cv2.resize(cv2.remap(self.source,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  cut=cv2.resize(cv2.remap(self.cut,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  base=np.array(reference).astype('float32');base[:,:,:3]*=base[:,:,3:4]/255;base*=1-cut[:,:,None]
  candidate=Image.fromarray(np.rint(np.clip(straight(over(base,part)),0,255)).astype('uint8'))
  return reference,candidate,dict(minimumTriangleArea2=minimum,lipCenter=oral[20].tolist(),chinY=float(self.head.exposure_skin[46,1]))
