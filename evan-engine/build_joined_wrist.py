"""Register a continuous wrist skin from existing forearm/hidden-palm art."""
import json,hashlib
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_index import smooth

def build(root=ROOT):
    arm_path=root/'body-rig/arm-right.png';palm_path=root/'index-rig/palm-source.png'
    distal_path=root/'index-rig/palm.png'
    old=np.asarray(Image.open(arm_path).convert('RGBA'));palm=np.asarray(Image.open(palm_path).convert('RGBA')).astype('float32');palm[:,:,:3]*=palm[:,:,3:4]/255
    meta=json.loads((root/'hand-rig/manifest.json').read_text());m=np.array(meta['matrix'],np.float32)
    palm=cv2.warpAffine(palm,m,(1024,1536),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    origin=np.array([810.,762.]);axis=np.array([61.,137.]);axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]])
    sections=np.arange(-65,41,dtype=float);q=np.arange(-90,90.01,.25)
    xy=origin+sections[:,None,None]*axis+q[None,:,None]*normal
    widths=[];centers=[]
    for a in [old,palm]:
        alpha=cv2.remap(a[:,:,3].astype('float32'),xy[:,:,0].astype('float32'),xy[:,:,1].astype('float32'),cv2.INTER_LINEAR)
        limits=[]
        for row in alpha:
            visible=q[row>=127.5]
            if not len(visible):raise ValueError('Missing wrist cross section')
            limits.append([visible[0],visible[-1]])
        limits=np.array(limits);widths.append(limits[:,1]-limits[:,0]);centers.append(limits.mean(axis=1))
    scale=widths[0]/widths[1];shift=centers[0]-scale*centers[1]
    # Smooth the measured silhouette fit; never change hand anatomy distal to
    # the 40-pixel wrist band. This is registration, not a new drawn hand.
    kernel=np.ones(7)/7
    scale=np.convolve(np.pad(scale,3,mode='edge'),kernel,mode='valid');shift=np.convolve(np.pad(shift,3,mode='edge'),kernel,mode='valid')
    yy,xx=np.mgrid[:1536,:1024];s=(xx-origin[0])*axis[0]+(yy-origin[1])*axis[1];n=(xx-origin[0])*normal[0]+(yy-origin[1])*normal[1]
    fit=1-smooth(s/40);sc=1+(np.interp(s,sections,scale)-1)*fit;sh=np.interp(s,sections,shift)*fit
    srcn=(n-sh)/sc;mx=(origin[0]+s*axis[0]+srcn*normal[0]).astype('float32');my=(origin[1]+s*axis[1]+srcn*normal[1]).astype('float32')
    aligned=cv2.remap(palm,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);aligned[s>=40]=palm[s>=40]
    blend=smooth((s+36)/24)[:,:,None];original=old.astype('float32');original[:,:,:3]*=original[:,:,3:4]/255
    joined=original*(1-blend)+aligned*blend;joined[:,:,:3]*=255/np.maximum(joined[:,:,3:4],1)
    joined=np.clip(joined,0,255).astype('uint8');joined[s<=-36]=old[s<=-36]
    distal=np.asarray(Image.open(distal_path).convert('RGBA'));joined[s>=40]=distal[s>=40]
    folder=root/'wrist-rig';folder.mkdir(exist_ok=True);Image.fromarray(joined).save(folder/'right-skin.png');Image.fromarray((blend[:,:,0]*255).astype('uint8')).save(folder/'blend-mask.png')
    report=dict(animationReady=False,sourceSha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [arm_path,palm_path,distal_path]},wrist=origin.tolist(),axis=axis.tolist(),crossSectionMethod='alpha>=127.5 sampled every .25 pixel, 7-section smoothed width/center fit',blendBand=[-36,-12],fitReleaseBand=[0,40],sections=sections.tolist(),widthScale=scale.tolist(),centerShift=shift.tolist(),limitations=['Local color/outline blending still needs artist review','One continuous skin surface retains wrist bones; palm is no longer a separate runtime pixel layer','Thumb and three neighboring fingers remain drawn together'])
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':cv2.setNumThreads(1);r=build();print(json.dumps({k:r[k] for k in ['animationReady','blendBand','fitReleaseBand']}))
