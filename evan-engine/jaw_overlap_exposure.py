"""Review-only upper-face / painted jaw / neck stack. No default promotion.

The upper-face cheek wings reuse existing artwork with explicit ownership;
no new cheek or upper-lip drawings are claimed. Neck backing is newly drawn.
"""
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from layered_cartoon_head import over,straight
from guided_jaw_exposure import GuidedJawExposure,target_mesh,fields,X,Y,SOURCE

# Native ownership interface. Side cheek wings stay in front of the jaw;
# the central opening remains the existing mouth, not a new painted upper lip.
INTERFACE=np.array([(128,288),(145,330),(164,361),(181,380),(190,369),(194,343),(201,327),(211,327),(228.5,328.5),(246,327),(256,326),(263,342),(278,363),(304,353),(329,335),(350,330),(384,288)],np.float32)

def mapped_interface(target):
 points=[]
 for point in INTERFACE:
  i=int(np.clip(np.searchsorted(X,point[0],side='right')-1,0,len(X)-2));j=int(np.clip(np.searchsorted(Y,point[1],side='right')-1,0,len(Y)-2))
  u=(point[0]-X[i])/(X[i+1]-X[i]);v=(point[1]-Y[j])/(Y[j+1]-Y[j]);a=j*len(X)+i;b=a+1;c=a+len(X);d=c+1
  ids=[a,b,d] if v<=u else [a,d,c]
  matrix=cv2.getAffineTransform(SOURCE[ids],target[ids]);points.append(matrix[:,:2]@point+matrix[:,2])
 return np.asarray(points,np.float32)

def upper_ownership(target):
 # Draw the forward-mapped boundary and fill to the canvas top. Remapping a
 # finite mesh's coverage loses the strip above its displaced top row.
 interface=mapped_interface(target)
 polygon=np.vstack([[[0,0],[511,0],[511,288]],interface[::-1],[[0,288]]]).astype('float32')
 raw=np.zeros((1536,1536),np.uint8);cv2.fillPoly(raw,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8)
 return cv2.resize(raw,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255


class JawOverlapExposure(GuidedJawExposure):
 def __init__(self):
  super().__init__();folder=ROOT/'jaw-overlap-v1'
  for name in ['Jaw','Neck']:
   part=np.array(Image.open(folder/(name+'.png')).convert('RGBA')).astype('float32');part[:,:,:3]*=part[:,:,3:4]/255;setattr(self,name.lower(),part)
 def at(self,t,plan):
  baseline=self.head.at(t,plan)
  if self.head.painted_rim is None:raise ValueError('Full F/V overlap assembly unsupported')
  oral=self.head.last_painted_target;target,minimum=target_mesh(oral,self.head.exposure_skin);maps=fields(target)
  jaw=cv2.resize(cv2.remap(self.jaw,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  # No alpha cleanup: source skin, painted overlap and silhouettes remain.
  owned=upper_ownership(target)
  if not np.all(owned[:315,190:280]==1):raise ValueError('Upper-face/nose ownership lost coverage')
  carrier=np.array(baseline).astype('float32');carrier[:,:,:3]*=carrier[:,:,3:4]/255;carrier*=owned[:,:,None]
  self.last_ownership=owned.copy()
  parts={'Neck backing':self.neck.copy(),'Jaw and lower lip combined':jaw,'Upper face with cheek wings':carrier}
  assembled=np.zeros_like(jaw)
  for part in parts.values():assembled=over(assembled,part)
  self.last_parts=parts
  old_part=cv2.resize(cv2.remap(self.source,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  old_cut=cv2.resize(cv2.remap(self.cut,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  old_base=np.array(baseline).astype('float32');old_base[:,:,:3]*=old_base[:,:,3:4]/255;old_base*=1-old_cut[:,:,None]
  self.previous_exposure=Image.fromarray(np.rint(np.clip(straight(over(old_base,old_part)),0,255)).astype('uint8'))
  candidate=Image.fromarray(np.rint(np.clip(straight(assembled),0,255)).astype('uint8'))
  nose_delta=int(np.max(abs(np.array(baseline)[288:315,190:280].astype(int)-np.array(candidate)[288:315,190:280].astype(int))))
  if nose_delta>1:raise ValueError(f'Upper nose changed beyond alpha sampling tolerance: {nose_delta}')
  # Color/coverage differences are diagnostic; this stack is not anatomy ready.
  return baseline,candidate,dict(minimumTriangleArea2=minimum,lipCenter=oral[20].tolist(),chinY=float(self.head.exposure_skin[46,1]),noseMaximumRGBAChange=nose_delta,upper288RowsExact=bool(np.array_equal(np.array(baseline)[:288],np.array(candidate)[:288])))
