"""Register mouth-free skin and recover a bounded source mouth-paint layer.

The paint layer still combines lip/interior/tongue. It is NOT a separated rig.
"""
import json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from audit_cartoon_construction import source_components,fit_pose


def split_paint(source,skin,box):
    """Minimum valid opacity against a known background, inside explicit ROI.

This is a derived matte, not recovered artist-original alpha. No color key.
    """
    foreground=source[:,:,:3].astype('float32')/255;background=skin[:,:,:3].astype('float32')/255;delta=foreground-background
    capacity=np.where(delta>=0,1-background,background)
    alpha=np.max(abs(delta)/np.maximum(capacity,1e-6),axis=2)
    keep=np.zeros(alpha.shape,bool);x0,y0,x1,y1=box;keep[y0:y1,x0:x1]=True;alpha=np.where(keep,np.clip(alpha,0,1),0)
    rgb=background+delta/np.maximum(alpha[:,:,None],1e-6)
    rgba=np.dstack([np.clip(rgb,0,1)*255,alpha*255]);paint=np.rint(rgba).astype('uint8')
    a=paint[:,:,3:4].astype(float)/255;rebuilt=paint[:,:,:3]*a+skin[:,:,:3]*(1-a)
    error=float(abs(rebuilt[y0:y1,x0:x1]-source[y0:y1,x0:x1,:3]).mean())
    return paint,error


def working_skin_patch(original,clean):
    yy,xx=np.mgrid[:512,:512];radius=np.sqrt(((xx-237)/65)**2+((yy-337)/29)**2)
    u=np.clip((1-radius)/.3,0,1);blend=u*u*(3-2*u);blend[yy<=310]=0
    # Calibrate local skin color on cheek samples, excluding mouth and nose.
    sample=(yy>=310)&(yy<374)&(xx>=172)&(xx<315)&(original[:,:,3]>240)&(clean[:,:,3]>240)&(radius>=1)&(radius<1.45)
    offset=np.median(original[:,:,:3].astype(float)[sample]-clean[:,:,:3].astype(float)[sample],axis=0)
    adjusted=np.clip(clean[:,:,:3].astype(float)+offset,0,255);out=original.copy();out[:,:,:3]=np.rint(original[:,:,:3]*(1-blend[:,:,None])+adjusted*blend[:,:,None]).astype('uint8')
    return out,blend,offset


def build(root=ROOT):
    folder=root/'construction-skin-v1';raw=np.array(Image.open(folder/'source/clean-skin-v1.png').convert('RGBA'));boxes=source_components(Image.fromarray(raw));rows=[]
    for name,box,roi in zip(['Seal','Release','Rounded'],boxes,[(186,315,278,350),(192,312,276,352),(192,306,278,362)]):
        # References are reproducibly fitted from the prior source construction.
        reference=np.array(Image.open(folder/f'references/{name}.png').convert('RGBA'));clean,report=fit_pose(raw,box,reference)
        if not report['upperFaceDiagnosticPass']:raise ValueError('Clean plate upper face failed diagnostic bounds')
        Image.fromarray(clean).save(folder/f'{name}-skin.png');paint,error=split_paint(reference,clean,roi);Image.fromarray(paint).save(folder/f'{name}-paint.png');rows.append(dict(pose=name,**report,paintROI=roi,reconstructionMeanRgbError=error))
    original=np.array(Image.open(root/'oral-rig/face-skin.png').convert('RGBA'));clean=np.array(Image.open(folder/'Seal-skin.png').convert('RGBA'));working,mask,offset=working_skin_patch(original,clean);Image.fromarray(working).save(folder/'working-face-skin.png');Image.fromarray(np.rint(mask*255).astype('uint8')).save(folder/'working-mask.png')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report=dict(sourceSha256=sha(folder/'source/clean-skin-v1.png'),referenceSha256={name:sha(folder/f'references/{name}.png') for name in ['Seal','Release','Rounded']},originalSkinSha256=sha(root/'oral-rig/face-skin.png'),poses=rows,workingSkin=dict(center=[237,337],radius=[65,29],innerBlendFraction=.3,noseGuardY=310,localRgbOffset=offset.tolist(),originalAlphaExact=bool(np.array_equal(working[:,:,3],original[:,:,3])),outsideMaskExact=bool(np.array_equal(working[mask==0],original[mask==0]))),paintType='derived minimum-opacity combined mouth paint; NOT independent lip/cavity/tongue',jawLayerSeparated=False,animationReady=False,limits=['One registered underpainting plane only in optional runtime profile','Remaining separated lip/interior/jaw parts and correspondence still needed'])
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':cv2.setNumThreads(1);r=build();print(json.dumps(dict(workingSkin=r['workingSkin'],poses=[dict(pose=p['pose'],ecc=p['upperFaceECC'],error=p['reconstructionMeanRgbError']) for p in r['poses']]),indent=2))
