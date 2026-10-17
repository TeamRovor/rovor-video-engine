"""Register complete cartoon head drawings without equal-grid clipping.
Output plates remain separate layers; a stable upper face is shared at runtime.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from audit_cartoon_sources import audit_atlas
from build_painted_rig import key_plate

ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'
SIZE=512

def affine_rgba(raw,matrix,inverse=False):
    a=np.asarray(raw).astype('float32');a[:,:,:3]*=a[:,:,3:4]/255
    a=cv2.warpAffine(a,matrix,(SIZE,SIZE),flags=cv2.INTER_CUBIC|(cv2.WARP_INVERSE_MAP if inverse else 0),borderMode=cv2.BORDER_CONSTANT)
    a[:,:,:3]=a[:,:,:3]*255/np.maximum(a[:,:,3:4],1)
    return np.clip(a,0,255).astype('uint8')

def build(source,output):
    source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest();audit=audit_atlas(source)
    raw=np.asarray(key_plate(Image.open(source)));plates=[];reports={}
    for cell in audit['cells']:
        x0,y0,x1,y1=cell['foregroundBox'];cx=(x0+x1)/2;cy=(y0+y1)/2
        matrix=np.array([[1,0,SIZE/2-cx],[0,1,SIZE/2-cy]],np.float32)
        # Mask the single component region before moving it; other heads must
        # never intrude into the new canvas through generous crop padding.
        isolated=np.zeros_like(raw);isolated[y0:y1,x0:x1]=raw[y0:y1,x0:x1]
        plates.append(affine_rgba(isolated,matrix));reports[cell['symbol']]={'source_box':cell['foregroundBox'],'placement':matrix.tolist()}
    gray=lambda a:cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((SIZE,SIZE),np.uint8);mask[50:290,90:445]=255
    base=plates[0]
    for i,symbol in enumerate('XABCDEFGH'):
        matrix=np.eye(2,3,dtype='float32');score=1.
        if i:
            score,matrix=cv2.findTransformECC(gray(base),gray(plates[i]),matrix,cv2.MOTION_EUCLIDEAN,
                (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-6),mask,5)
            if score<.95 or abs(matrix[0,1])>.04 or np.max(np.abs(matrix[:,2]))>12:
                raise ValueError(f'Identity-distorting registration for {symbol}: {score}, {matrix}')
        aligned=affine_rgba(plates[i],matrix,True)
        Image.fromarray(aligned).save(output/f'head-{symbol}.png')
        reports[symbol].update(ecc=float(score),registration=matrix.tolist())
    yy=np.mgrid[:SIZE,:SIZE][0];weight=np.clip((yy-292)/16,0,1)
    Image.fromarray(np.rint(weight*255).astype('uint8')).save(output/'lower-face-weight.png')
    manifest=dict(version=1,canvas=[SIZE,SIZE],source_sha256=digest,source_file=source.name,registration=reports,
        status='experimental registered head component; full-character rig incomplete',animationReady=False,
        limitations=['Narrow-mouth and teeth blends remain soft/doubled in some frames','FV drawing still reads as grimace','Body/arms/hands not assembled'])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise RuntimeError('Source changed')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'source/speech-poses-v2.png');p.add_argument('--output',type=Path,default=ROOT/'head-rig');a=p.parse_args();print(json.dumps(build(a.source,a.output)['registration'],indent=2))
