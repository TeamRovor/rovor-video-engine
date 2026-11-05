"""Build a registered painted Evan rig from generated, author-reviewed source plates.

Unlike the rejected V4 studies, no skin inpainting or geometric lip replacement
occurs. Full lower-face drawings provide lips, cheeks, teeth, tongue and chin.
Pillow/NumPy/OpenCV are build dependencies. Sources are immutable.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parent.parent/'evan-character/painted-v1'
SYMBOLS='XABCDEFGH'
# Source coordinates on the 1024x1536 setup plate; image-space x right/y down.
ARMS={
 'left':{'shoulder':[242,492],'elbow':[205,752],'wrist':[130,978],'tip':[92,1058],
         'polygon':[(223,431),(299,477),(331,604),(294,720),(275,790),(255,848),(214,974),(182,1038),(178,1107),(12,1110),(10,923),(84,910),(102,815),(138,741),(150,638),(162,524)]},
 'right':{'shoulder':[751,514],'elbow':[796,755],'wrist':[872,1019],'tip':[936,1090],
          'polygon':[(749,462),(798,490),(825,611),(815,676),(849,746),(883,847),(915,969),(1018,964),(1023,1158),(844,1155),(836,1071),(813,1004),(776,928),(751,846),(709,790),(705,723),(689,654),(702,548)]}
}

def key_plate(im):
    """Chroma composite matte. Keys magenta, never white teeth or skin highlights."""
    a=np.asarray(im.convert('RGBA')).astype(np.float32)
    dominance=np.minimum(a[:,:,0],a[:,:,2])-a[:,:,1]
    alpha=np.clip((115-dominance)/65,0,1)
    # Straight RGB at partial-alpha edges; keep solid interior exactly intact.
    bg=np.array([255,0,255],np.float32)
    rgb=np.clip((a[:,:,:3]-(1-alpha[:,:,None])*bg)/np.maximum(alpha[:,:,None],.02),0,255)
    rgb[alpha<.02]=0
    return Image.fromarray(np.dstack((rgb,alpha*255)).astype('uint8'))

def polygon_layer(im,pts,feather=1):
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon(pts,fill=255)
    if feather: mask=mask.filter(ImageFilter.GaussianBlur(feather))
    a=np.asarray(im).copy();a[:,:,3]=(a[:,:,3].astype(float)*np.asarray(mask)/255).astype('uint8')
    return Image.fromarray(a)

def register_face(base,face):
    gray=lambda im: cv2.cvtColor(np.array(im)[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((418,418),np.uint8);mask[45:205,95:365]=255
    matrix=np.eye(2,3,dtype='float32')
    try:
        score,matrix=cv2.findTransformECC(gray(base),gray(face),matrix,cv2.MOTION_AFFINE,
           (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,150,1e-5),mask,5)
    except cv2.error as e:
        raise RuntimeError('Face registration failed; inspect atlas') from e
    if score<.9 or np.max(np.abs(matrix[:,:2]-np.eye(2)))>.08:
        raise ValueError(f'Face registration would distort identity: score {score}, matrix {matrix}')
    rgba=cv2.warpAffine(np.asarray(face),matrix,(418,418),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,
                        borderMode=cv2.BORDER_CONSTANT)
    return Image.fromarray(rgba),float(score),matrix.tolist()

def build(source,destination):
    source,destination=Path(source),Path(destination);destination.mkdir(parents=True,exist_ok=True)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.png')}
    master=key_plate(Image.open(source/'master.png'));torso=key_plate(Image.open(source/'torso.png'))
    torso.save(destination/'torso.png')
    for name,geo in ARMS.items(): polygon_layer(master,geo['polygon']).save(destination/f'arm-{name}.png')
    atlas=Image.open(source/'facial-poses-v2.png').convert('RGBA')
    if atlas.size!=(1254,1254):raise ValueError('Atlas must be 1254x1254; recalibrate grid if regenerated')
    faces=[key_plate(atlas.crop(((i%3)*418,(i//3)*418,(i%3+1)*418,(i//3+1)*418))) for i in range(9)]
    report={}
    registered=[]
    for i,(symbol,face) in enumerate(zip(SYMBOLS,faces)):
        aligned,score,matrix=register_face(faces[0],face) if i else (face,1,np.eye(2,3).tolist())
        aligned.save(destination/f'face-{symbol}-full.png')
        # Exclude portrait shirt shoulders; retain head plus natural neck overlap.
        pts=[(0,0),(418,0),(418,285),(320,285),(300,325),(286,369),(205,386),(167,361),(132,323),(105,287),(0,287)]
        head=polygon_layer(aligned,pts,1.2)
        head.save(destination/f'head-{symbol}.png');registered.append(head)
        report[symbol]={'upper_face_ecc':round(score,5),'registration_matrix':matrix}
    # Keep upper face/hair absolutely stable; interpolate entire lower face/jaw,
    # not rectangular mouth stickers. This mask blends below glasses and nose.
    yy,xx=np.mgrid[:418,:418]
    blend=np.clip((yy-210)/30,0,1).astype('float32')
    Image.fromarray((blend*255).astype('uint8')).save(destination/'lower-face-weight.png')
    # Whole painted drawings use fixed landmark correspondence in the renderer.
    manifest={'version':1,'status':'development; visual acceptance required',
      'canvas':[1024,1536],'head_transform':{'scale':1.1,'translate':[290,8],'pivot':[535,379]},
      'arms':ARMS,'face_order':list(SYMBOLS),'face_registration':report,'source_sha256':before,
      'facial_method':'registered complete lower-face drawings; anatomical landmark mesh interpolation',
      'limitations':['No native Moho project verified','No depth rotation beyond fixed 3/4 view',
       'Generated FV/L artwork needs anatomical review','Only one open-hand drawing per side; no finger controls',
       'Head atlas cells are 418px; native final detail is limited by source resolution']}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.png')}
    if before!=after:raise RuntimeError('Builder modified source art')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'source');p.add_argument('--output',type=Path,default=ROOT/'rig');a=p.parse_args()
    m=build(a.source,a.output);print(json.dumps(m['face_registration'],indent=2))
