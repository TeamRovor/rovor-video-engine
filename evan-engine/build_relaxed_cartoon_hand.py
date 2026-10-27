"""Register a drawn alternate hand and fit only its proximal wrist overlap.

Generated alpha retained. Fingers stay one drawing; no invented phalange rig.
"""
import json,hashlib,math
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_index import smooth

def build(root=ROOT,*,folder_name='relaxed-hand-v1',source_name='source/right-relaxed-v2.png',source_wrist=(531.,500.),source_scale=.16,source_antialias=False):
 folder=root/folder_name;source=folder/source_name;arm_path=root/'body-rig/arm-right.png';old=np.asarray(Image.open(arm_path).convert('RGBA'));raw=np.asarray(Image.open(source).convert('RGBA')).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
 pivot=np.asarray(source_wrist,float)
 if pivot.shape!=(2,) or not np.isfinite(pivot).all():raise ValueError('Expected finite source wrist coordinates')
 if not np.isfinite(source_scale) or source_scale<=0:raise ValueError('Expected positive finite source scale')
 if source_antialias and source_scale<1:
  # Filter associated color/alpha over the source footprint before minification.
  sigma=.5*math.sqrt(source_scale**-2-1);raw=cv2.GaussianBlur(raw,(0,0),sigmaX=sigma,sigmaY=sigma,borderType=cv2.BORDER_CONSTANT)
 origin=np.array([810.,762.]);angle=math.radians(15);linear=source_scale*np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]);matrix=np.c_[linear,origin-linear@pivot].astype('float32');palm=cv2.warpAffine(raw,matrix,(1024,1536),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);palm=np.clip(palm,0,255)
 axis=np.array([61.,137.]);axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]]);sections=np.arange(-65,41,dtype=float);q=np.arange(-110,110.01,.25);xy=origin+sections[:,None,None]*axis+q[None,:,None]*normal;widths=[];centers=[]
 for image in [old,palm]:
  alpha=cv2.remap(image[:,:,3].astype('float32'),xy[:,:,0].astype('float32'),xy[:,:,1].astype('float32'),cv2.INTER_LINEAR);limits=[]
  for row in alpha:
   visible=q[row>=127.5]
   if not len(visible):raise ValueError('Missing wrist cross section')
   limits.append([visible[0],visible[-1]])
  limits=np.array(limits);widths.append(limits[:,1]-limits[:,0]);centers.append(limits.mean(axis=1))
 scales=widths[0]/widths[1];shifts=centers[0]-scales*centers[1];kernel=np.ones(7)/7;scales=np.convolve(np.pad(scales,3,mode='edge'),kernel,mode='valid');shifts=np.convolve(np.pad(shifts,3,mode='edge'),kernel,mode='valid');yy,xx=np.mgrid[:1536,:1024];s=(xx-origin[0])*axis[0]+(yy-origin[1])*axis[1];n=(xx-origin[0])*normal[0]+(yy-origin[1])*normal[1];fit=1-smooth(s/40);sc=1+(np.interp(s,sections,scales)-1)*fit;sh=np.interp(s,sections,shifts)*fit;srcn=(n-sh)/sc;mx=(origin[0]+s*axis[0]+srcn*normal[0]).astype('float32');my=(origin[1]+s*axis[1]+srcn*normal[1]).astype('float32');aligned=cv2.remap(palm,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);aligned[s>=40]=palm[s>=40]
 blend=smooth((s+36)/24)[:,:,None];original=old.astype('float32');original[:,:,:3]*=original[:,:,3:4]/255;joined=original*(1-blend)+aligned*blend;joined[:,:,:3]*=255/np.maximum(joined[:,:,3:4],1);joined=np.clip(joined,0,255).astype('uint8');joined[s<=-36]=old[s<=-36];Image.fromarray(joined).save(folder/'right-skin.png')
 registered=palm.copy();registered[:,:,:3]*=255/np.maximum(registered[:,:,3:4],1);Image.fromarray(np.clip(registered,0,255).astype('uint8')).save(folder/'registered-hand.png');Image.fromarray((blend[:,:,0]*255).astype('uint8')).save(folder/'blend-mask.png')
 meta=dict(animationReady=False,mode='built-in image_gen source; deterministic registration',sourceSize=[raw.shape[1],raw.shape[0]],sourceSha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,arm_path,root/'source/design-sheet-v1.png',root/'hand-source/right-point-v1.png']},sourceWrist=pivot.tolist(),targetWrist=origin.tolist(),sourceToBody=matrix.tolist(),registration='manually inspected wrist/axis; no whole-image similarity claim',axis=axis.tolist(),blendBand=[-36,-12],fitReleaseBand=[0,40],sections=sections.tolist(),widthScale=scales.tolist(),centerShift=shifts.tolist(),limitations=['One alternate drawn hand; all five digits share wrist transform','No interpolated point/open finger transition or pose switching in this study','Wrist color/line fit is registration, not a redrawn anatomical joint','Source and posed joins require human artist review'])
 if source_antialias and source_scale<1:meta['registrationPrefilter']=dict(method='Gaussian on associated RGBA before cubic affine minification',sigmaSourcePixels=sigma,rawSourceUnmodified=True,sourceAlphaCleaned=False,derivativeAlphaResampled=True)
 (folder/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':cv2.setNumThreads(1);print(json.dumps(build(),indent=2))
