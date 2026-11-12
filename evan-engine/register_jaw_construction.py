"""Source-only jaw registration diagnostic; never loads a runtime profile.

Semantic anchors are explicitly authored from opaque native source previews.
Three edge anchors fit an affine transform. Held-out lip/chin anchors test fit;
alpha is retained, premultiplied for sampling. An overlay is NOT an assembly.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from render_cartoon_head_study import font

# Coordinates in the unmodified 2172x724 source plate. Broad jaw planes,
# not independently painted upper/lower lips. No auto-registration claim.
SOURCE=np.array([[887,279],[1520,264],[1125,541],[1150,347],[970,492]],np.float32)
TARGET=np.array([[164,315],[329,320],[220,394],[231,330],[194,387]],np.float32)
NAMES=['left cheek overlap','right jaw hinge overlap','chin silhouette','lower lip center (held out)','left chin bend (held out)']


def composite(raw,color='#f3eee2'):
    image=Image.fromarray(raw);out=Image.new('RGBA',image.size,color);out.alpha_composite(image);return out.convert('RGB')


def register(source,reference,output):
    output.mkdir(parents=True,exist_ok=True);raw=np.array(Image.open(source).convert('RGBA'));ref=np.array(Image.open(reference).convert('RGBA'))
    if raw.shape[:2]!=(724,2172):raise ValueError('Anchor calibration is only for the recorded source dimensions')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    # Rectangular isolation only in the transparent gutters. The painted jaw
    # and its generated alpha are copied exactly, including tiny edge pixels.
    region=(860,200,1560,600);x0,y0,x1,y1=region
    part=raw[y0:y1,x0:x1].copy();Image.fromarray(part).save(output/'Jaw-Source-Part.png')
    associated=part.astype('float32');associated[:,:,:3]*=associated[:,:,3:4]/255
    matrix=cv2.getAffineTransform((SOURCE[:3]-np.array([x0,y0],np.float32)).astype('float32'),TARGET[:3])
    sampled=cv2.warpAffine(associated,matrix*3,(1536,1536),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    sampled=cv2.resize(sampled,(512,512),interpolation=cv2.INTER_AREA)
    result=sampled.copy();result[:,:,:3]*=255/np.maximum(result[:,:,3:4],1);result=np.rint(np.clip(result,0,255)).astype('uint8');Image.fromarray(result).save(output/'Registered-Jaw-Study.png')
    full_matrix=matrix.copy();full_matrix[:,2]-=matrix[:,:2]@np.array([x0,y0],np.float32)
    mapped=SOURCE@full_matrix[:,:2].T+full_matrix[:,2];residual=np.linalg.norm(mapped-TARGET,axis=1)
    overlap=Image.fromarray(ref);over=Image.fromarray(result);over.putalpha(Image.fromarray(np.rint(result[:,:,3]*.55).astype('uint8')));overlap.alpha_composite(over)
    sheet=Image.new('RGB',(1600,740),'#f3eee2');d=ImageDraw.Draw(sheet)
    for i,(label,img) in enumerate([('Construction reference',composite(ref)),('55% overlay / NOT an assembly',composite(np.array(overlap))),('Isolated registered jaw / SOURCE ONLY',composite(result))]):
        ox=10+i*530;sheet.paste(img,(ox,85));d.text((ox+5,35),label,font=font(20),fill='#253c49')
        for j,(a,b) in enumerate(zip(mapped,TARGET)):
            if i==1:
                d.line((ox+a[0],85+a[1],ox+b[0],85+b[1]),fill='#d13740',width=2)
                for p,c in [(a,'#d13740'),(b,'#007d80')]:d.ellipse((ox+p[0]-3,85+p[1]-3,ox+p[0]+3,85+p[1]+3),fill=c)
    d.text((25,625),f'Held-out lower-lip error {residual[3]:.2f}px; chin-bend error {residual[4]:.2f}px at native 512px head scale.',font=font(24),fill='#253c49')
    d.text((25,668),'Jaw source has no neck or enclosed mouth; lacks a lower-lip roll. Upper-muzzle source still contains a complete mouth.',font=font(20),fill='#253c49')
    d.text((25,705),'No skin extraction, color key or whole-head swaps. Needs redrawn correspondence and overlap before animation.',font=font(20),fill='#253c49');sheet.save(output/'Registration-Review.png')
    report=dict(source=str(source),sourceSha256=before,reference=str(reference),referenceSha256=hashlib.sha256(reference.read_bytes()).hexdigest(),sourceRegion=region,partPixelsAndAlphaExact=bool(np.array_equal(part,raw[y0:y1,x0:x1])),sourceModified=False,registration='three manually authored affine edge anchors; remaining anchors held out',matrixFullSourceTo512=full_matrix.tolist(),anchors=[dict(name=n,source=s.tolist(),target=t.tolist(),mapped=m.tolist(),residualPixels=float(r),usedForFit=i<3) for i,(n,s,t,m,r) in enumerate(zip(NAMES,SOURCE,TARGET,mapped,residual))],assemblyReady=False,runtimeLoaded=False,missing=['Designed lower-lip roll and pressure/contact key drawings','Compatible independent upper muzzle/lip (current source includes a complete mouth)','Verified cheek/neck occlusion and jaw overlap','Voiced normal/slow performance'],decision='REJECT affine registration for animation; semantic lower-lip/chin residuals and missing lip anatomy remain')
    assert before==hashlib.sha256(source.read_bytes()).hexdigest();(output/'Registration-Audit.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(register(a.source,a.reference,a.output),indent=2))
