"""Inspect generated full-face construction poses before layer registration.

Upper-face affine fitting is a diagnostic, not permission to swap full heads.
Source alpha is retained. Lower-face drawings are deliberately excluded from ECC.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from render_cartoon_head_study import font


def source_components(image,expected=3):
    a=np.asarray(image.convert('RGBA'));count,labels,stats,_=cv2.connectedComponentsWithStats((a[:,:,3]>=16).astype('uint8'),8)
    ids=sorted(range(1,count),key=lambda i:int(stats[i,4]),reverse=True)[:expected]
    if len(ids)!=expected or min(int(stats[i,4]) for i in ids)<1000:raise ValueError('Expected three separate substantial heads')
    boxes=[list(map(int,stats[i,:4])) for i in ids];return sorted(boxes,key=lambda b:b[0])


def composite(raw):
    a=raw.astype('float32')/255
    return a[:,:,:3]*a[:,:,3:4]+np.array([243,238,226],float)/255*(1-a[:,:,3:4])


def fit_pose(raw,box,reference):
    x,y,w,h=box;crop=raw[y:y+h,x:x+w].copy();ry,rx=np.where(reference[:,:,3]>=16);left,top,right,bottom=rx.min(),ry.min(),rx.max()+1,ry.max()+1
    scale=(right-left)/w;matrix=np.array([[scale,0,left],[0,scale,top]],np.float32)
    associated=crop.astype('float32');associated[:,:,:3]*=associated[:,:,3:4]/255
    placed=cv2.warpAffine(associated,matrix,(512,512),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    def straight(a):
        b=a.copy();b[:,:,:3]*=255/np.maximum(b[:,:,3:4],1);return np.clip(b,0,255).astype('uint8')
    placed_raw=straight(placed);mask=np.zeros((512,512),np.uint8);mask[80:295,90:420]=255
    template=cv2.cvtColor(composite(reference).astype('float32'),cv2.COLOR_RGB2GRAY);sample=cv2.cvtColor(composite(placed_raw).astype('float32'),cv2.COLOR_RGB2GRAY)
    correction=np.eye(2,3,dtype='float32');score=None;failure=None
    try:
        score,correction=cv2.findTransformECC(template,sample,correction,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,120,1e-6),mask,5)
        aligned=cv2.warpAffine(placed,correction,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
    except cv2.error as error:failure=str(error).splitlines()[0];aligned=placed
    aligned=straight(aligned);delta=np.abs(composite(aligned)-composite(reference))*255
    upper=mask>0;linear=correction[:,:2];singular=np.linalg.svd(linear,compute_uv=False)
    # Conservative diagnostic bounds only. Registered planes/correspondences
    # are separate mandatory requirements and never inferred from this score.
    upper_fit_ok=score is not None and score>=.95 and np.max(abs(singular-1))<=.1 and np.max(abs(correction[:,2]))<=12
    report=dict(sourceBox=box,initialPlacement=matrix.tolist(),upperFaceCorrection=correction.tolist(),upperFaceECC=score,upperFaceMeanAbsRgbError=float(delta[upper].mean()),upperFaceDiagnosticPass=bool(upper_fit_ok),error=failure,registrationReady=False,animationReady=False,missing=['Separate skin, lip rim, cavity, teeth/tongue planes','Matched lip-corner/inner-lip/jaw correspondences','Verified normal/slow voiced performance'])
    return aligned,report


def audit(source,reference,output):
    source,reference,output=map(Path,(source,reference,output));output.mkdir(parents=True,exist_ok=True);raw=np.asarray(Image.open(source).convert('RGBA'));ref=np.asarray(Image.open(reference).convert('RGBA'));boxes=source_components(Image.fromarray(raw));reports=[];sheet=Image.new('RGB',(1600,620),'#f3eee2');d=ImageDraw.Draw(sheet)
    for i,(name,box) in enumerate(zip(['Seal','Release','Rounded'],boxes)):
        aligned,report=fit_pose(raw,box,ref);reports.append(dict(pose=name,**report));Image.fromarray(aligned).save(output/f'{name}-Aligned.png');head=Image.fromarray(aligned);sheet.paste(head,(15+i*530,65),head);d.text((25+i*530,20),f'{name} — SOURCE ONLY',font=font(21),fill='#253c49')
    sheet.save(output/'Aligned-Construction.png');result=dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),referenceSha256=hashlib.sha256(reference.read_bytes()).hexdigest(),sourceAlphaPreserved=True,poses=reports,animationReady=False,wholeHeadSwapsAllowed=False,limits='Upper-face ECC is diagnostic only; no source plate is a registered working layered rig.')
    (output/'Construction-Audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=audit(a.source,a.reference,a.output);print(json.dumps([{k:v for k,v in p.items() if k in ['pose','upperFaceECC','upperFaceMeanAbsRgbError','upperFaceDiagnosticPass','registrationReady']} for p in r['poses']],indent=2))
