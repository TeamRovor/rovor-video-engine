"""Original cartoon body components, FK metadata and candidate registration gate."""
import hashlib,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'
LEFT=[(300,340),(280,390),(265,480),(245,535),(240,578),(236,622),(211,641),(177,739),(115,790),(115,840),(140,880),(150,930),(230,930),(268,880),(258,830),(252,786),(279,708),(310,675),(326,640),(338,598),(371,545),(380,480),(387,411),(380,369)]
ARMS={
 'left':dict(shoulder=[340,405],elbow=[275,625],wrist=[202,784],polygon=LEFT),
 'right':dict(shoulder=[684,405],elbow=[749,625],wrist=[822,784],polygon=[(1024-x,y) for x,y in LEFT])}

def masked(image,points):
    mask=Image.new('L',image.size);ImageDraw.Draw(mask).polygon(points,fill=255);mask=mask.filter(ImageFilter.GaussianBlur(.7))
    a=np.asarray(image).copy();a[:,:,3]=(a[:,:,3].astype(float)*np.asarray(mask)/255).astype('uint8')
    return Image.fromarray(a)

def register_body(master,plate):
    raw=np.asarray(plate.resize(master.size,Image.Resampling.LANCZOS)).copy();base=np.asarray(master)
    def gray(a):
        # Hidden RGB in transparent pixels is not artwork. Compare both plates
        # on a common matte so discarded head/leg-gap pixels cannot drive ECC.
        alpha=a[:,:,3:4].astype('float32')/255
        rgb=a[:,:,:3].astype('float32')*alpha+np.array([243,238,226],dtype='float32')*(1-alpha)
        return cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)/255
    mask=np.zeros(base.shape[:2],np.uint8);mask[420:670,410:620]=255;mask[700:1200,360:670]=255
    mask[base[:,:,3]<240]=0
    mask=cv2.erode(mask,np.ones((7,7),np.uint8))
    matrix=np.eye(2,3,dtype='float32')
    score,matrix=cv2.findTransformECC(gray(base),gray(raw),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),mask,5)
    if score<.9 or np.max(abs(matrix[:,:2]-np.eye(2)))>.12:raise ValueError('Hidden body changed proportions; inspect before proceeding')
    f=raw.astype('float32');f[:,:,:3]*=f[:,:,3:4]/255
    f=cv2.warpAffine(f,matrix,master.size,flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
    f[:,:,:3]=f[:,:,:3]*255/np.maximum(f[:,:,3:4],1)
    return Image.fromarray(np.clip(f,0,255).astype('uint8')),dict(ecc=float(score),matrix=matrix.tolist())

def build(root=ROOT):
    output=root/'body-rig';output.mkdir(exist_ok=True)
    master=Image.open(root/'source/setup-v1.png').convert('RGBA')
    # Generated whole-body replacement failed registration. Preserve source
    # anatomy, including a short original upper-sleeve overlap at each socket.
    torso_points=[(450,301),(568,301),(568,322),(694,370),(717,453),(686,491),(651,520),(625,617),(630,657),(666,805),(741,1390),(842,1518),(189,1518),(325,1390),(354,805),(389,657),(395,617),(373,520),(338,491),(307,453),(327,370),(439,322)]
    torso=masked(master,torso_points);torso.save(output/'torso.png')
    report=dict(method='original setup polygon with original upper-sleeve overlap',generated_plate='rejected: changed shirt proportions; ECC gate failed')
    for name,g in ARMS.items():masked(master,g['polygon']).save(output/f'arm-{name}.png')
    meta=dict(version=1,canvas=list(master.size),registration=report,arms=ARMS,
        head_transform=dict(scale=.82,translate=[297,-24],pivot=[510,343]),
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'source/setup-v1.png',root/'body-source/torso-hidden-v1.png')},
        status='experimental body component; shoulder joins and neck registration require visual review',animationReady=False,
        limitations=['Original sleeve overlap only; armpit creases need redrawn hidden surfaces','One open hand per side; fingers not rigged','Legs are static','No native Moho project verified'])
    (output/'manifest.json').write_text(json.dumps(meta,indent=2));return meta
if __name__=='__main__':print(json.dumps(build(),indent=2))
