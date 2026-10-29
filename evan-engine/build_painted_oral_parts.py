"""Source-layer assembly diagnostic. Does not install a runtime mouth profile."""
import argparse, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from psd_tools import PSDImage
from audit_cartoon_construction import source_components
from cartoon_body import ROOT
from render_cartoon_head_study import font


def place(raw, box, target, size):
    """Resample original alpha and associated color; no color-key cleanup."""
    x,y,w,h=box; tx,ty,tw,th=target
    crop=raw[y:y+h,x:x+w].astype('float32')
    crop[:,:,:3]*=crop[:,:,3:4]/255
    matrix=np.array([[tw/w,0,tx],[0,th/h,ty]],np.float32)
    out=cv2.warpAffine(crop,matrix,size,flags=cv2.INTER_LINEAR)
    out[:,:,:3]*=255/np.maximum(out[:,:,3:4],1)
    return Image.fromarray(np.clip(out,0,255).astype('uint8'))


def match_cavity(cavity, rim):
    """Match each cavity column to the rim's filled outer silhouette.

    Original cavity color/alpha are resampled, not reconstructed from skin.
    Binary contour detection is analysis only; output edge uses rim alpha.
    This solves backing/occlusion for one pose, not cross-pose topology.
    """
    r=np.asarray(rim);c=np.asarray(cavity);h,w=r.shape[:2]
    inverse=(r[:,:,3]<16).astype('uint8')
    count,labels,stats,_=cv2.connectedComponentsWithStats(inverse,8)
    holes=[i for i in range(1,count) if stats[i,0]>0 and stats[i,1]>0
           and stats[i,0]+stats[i,2]<w and stats[i,1]+stats[i,3]<h and stats[i,4]>100]
    if len(holes)!=1:raise ValueError('Rim must enclose one substantial transparent aperture')
    contours,_=cv2.findContours((r[:,:,3]>=16).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    outer=np.zeros((h,w),np.uint8);cv2.drawContours(outer,contours,-1,255,cv2.FILLED)
    envelope=np.maximum(outer,r[:,:,3])
    yy,xx=np.where(outer>0);cy,cx=np.where(c[:,:,3]>=240)
    if len(cx)<100:raise ValueError('Cavity lacks an opaque painted interior')
    lo,hi=xx.min(),xx.max();clo,chi=cx.min(),cx.max()
    mapx=np.full((h,w),-1,np.float32);mapy=mapx.copy()
    for x in range(lo,hi+1):
        ys=np.where(outer[:,x]>0)[0]
        sx=int(round(clo+(chi-clo)*(x-lo)/max(hi-lo,1)))
        sy=np.where(c[:,sx,3]>=240)[0]
        if not len(ys) or not len(sy):continue
        # Sample the opaque cavity interior to back the entire rim aperture.
        mapx[ys,x]=sx;mapy[ys,x]=np.linspace(sy.min(),sy.max(),len(ys))
    associated=c.astype('float32');associated[:,:,:3]*=associated[:,:,3:4]/255
    out=cv2.remap(associated,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    out[:,:,:3]*=255/np.maximum(out[:,:,3:4],1)
    out[:,:,3]*=envelope/255
    return Image.fromarray(np.clip(out,0,255).astype('uint8')),envelope


def build(source, output):
    output.mkdir(parents=True,exist_ok=True)
    raw=np.asarray(Image.open(source).convert('RGBA'))
    boxes=source_components(Image.fromarray(raw))
    # Explicit diagnostic correspondences in a 640px inspection canvas.
    # Bounding rectangles do NOT establish lip-corner/inner-contour topology.
    targets=[(60,100,520,275),(66,107,508,258),(124,254,390,112)]
    layers={n:place(raw,b,t,(640,480)) for n,b,t in zip(['Rim','Cavity','Tongue'],boxes,targets)}
    layers['Cavity'],envelope=match_cavity(layers['Cavity'],layers['Rim'])
    tongue=np.array(layers['Tongue']);tongue[:,:,3]=(tongue[:,:,3].astype(float)*envelope/255).astype('uint8')
    layers['Tongue']=Image.fromarray(tongue)
    assembled=Image.new('RGBA',(640,480))
    for n in ['Cavity','Tongue','Rim']:assembled.alpha_composite(layers[n])
    assembled.save(output/'Rounded-Assembly.png')
    Image.fromarray(envelope).save(output/'Shared-Envelope.png')
    interior=cv2.erode(envelope,np.ones((7,7),np.uint8))>=250
    backing=np.asarray(layers['Cavity'])[:,:,3]
    holes=int(np.count_nonzero(interior&(backing<240)))
    assert holes==0,'Unbacked pixels inside shared mouth envelope'
    assert not np.any(tongue[:,:,3][envelope==0]),'Tongue escaped mouth silhouette'
    for n,im in layers.items():im.save(output/(n+'.png'))
    psd=PSDImage.frompil(Image.new('RGBA',(640,480)))
    for n in ['Cavity','Tongue','Rim']:psd.create_pixel_layer(layers[n],name=n+' — diagnostic placement')
    psd.save(output/'Rounded-Source-Layers.psd')
    reopened=PSDImage.open(output/'Rounded-Source-Layers.psd').composite(force=True,ignore_preview=True).convert('RGBA')
    def premul(im):
        a=np.asarray(im).astype(float);a[:,:,:3]*=a[:,:,3:4]/255;return a
    error=float(abs(premul(reopened)-premul(assembled)).mean());assert error<1
    skin=Image.open(ROOT/'construction-skin-v1/Rounded-skin.png').convert('RGBA')
    face=skin.copy()
    # The source rounded-vowel envelope, manually identified for comparison.
    # This is a static source study, never a rendered/runtime frame.
    for n in ['Cavity','Tongue','Rim']:
        part=layers[n].crop((60,100,580,375)).resize((57,29),Image.Resampling.LANCZOS)
        face.alpha_composite(part,(203,320))
    face.save(output/'Static-Face-Assembly.png')
    reference=Image.open(ROOT/'construction-skin-v1/references/Rounded.png').convert('RGBA')
    sheet=Image.new('RGB',(1600,1100),'#f3eee2');d=ImageDraw.Draw(sheet)
    for i,n in enumerate(['Rim','Cavity','Tongue']):
        im=layers[n].resize((480,360),Image.Resampling.LANCZOS)
        sheet.paste(im,(20+i*530,50),im);d.text((30+i*530,15),n+' / separate painted alpha',font=font(21),fill='#253c49')
    for x,label,im in [(20,'Source construction',reference),(550,'Static layer assembly — NOT RIGGED',face)]:
        sheet.paste(im,(x,480),im);d.text((x,435),label,font=font(22),fill='#253c49')
    crop=face.crop((184,306,280,365)).resize((480,295),Image.Resampling.NEAREST)
    sheet.paste(crop,(1100,560),crop);d.text((1100,510),'5x mouth pixels',font=font(23),fill='#253c49')
    sheet.save(output/'Source-Assembly-Review.png')
    report=dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceBoxes=boxes,
        diagnosticTargets=targets,workingEnvelope=[203,320,57,29],sourceFileAlphaUnmodified=True,
        resampling='Associated color; rim alpha resampled. Cavity column correspondence to rim envelope; tongue alpha clipped by shared envelope. Source files untouched.',
        psdMeanPremultipliedDifference=error,sourceLayers=['Cavity','Tongue','Rim'],
        unbackedInteriorPixels=holes,tongueOutsideEnvelopePixels=int(np.count_nonzero(tongue[:,:,3][envelope==0])),
        runtimeInstalled=False,animationReady=False,matchedInnerContour=False,jawSeparated=False,
        limits=['Manual box placement is a static source test, not mesh correspondence',
                'No seal/release counterparts or phone timing changed','No performance approval from PSD reconstruction'])
    (output/'Assembly-Audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(build(a.source,a.output),indent=2))
