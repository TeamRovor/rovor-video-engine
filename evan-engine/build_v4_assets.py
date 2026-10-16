"""Create conservative, pose-calibrated visemes using the user's original Evan art.

Offline build step; Pillow, NumPy and OpenCV are only required to REBUILD
assets, not for everyday video generation. V3 files remain untouched.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / 'evan-character'
SRC = ROOT / 'v3-assets'
OUT = ROOT / 'v4-assets'
BRAND = ROOT / 'brand'
LOGO_SOURCE = BRAND / 'source-original.png'
# Landmark coordinates refer to the exact V3 pose PNG at native resolution.
# Ranges have been calibrated against the original face, not against the
# full-frame character placement (which changes by camera framing).
CALIBRATION = {
 'neutral': {'center': (282, 179), 'cover': (32, 14), 'width': 45, 'angle': -15},
 'point':   {'center': (182, 144), 'cover': (28, 13), 'width': 40, 'angle': -16},
 'present': {'center': (223, 158), 'cover': (29, 16), 'width': 43, 'angle': -17},
}
# Restrict mouth extremes; the original art is not rigged for wide opening.
V4_SHAPES = {'rest': 'rest','MBP':'MBP', 'FV':'FV','L':'L','AE':'AE', 'O':'O','UW':'UW', 'open':'open','smile':'smile'}


def cleaned_skin(face, center, cover):
    rgba = np.asarray(face.convert('RGBA'))
    mask = np.zeros((rgba.shape[0], rgba.shape[1]), dtype=np.uint8)
    cv2.ellipse(mask,center,cover,0,0,360,255,-1,cv2.LINE_AA)
    # Avoid the OpenCV alpha channel interpolating over transparency.
    rgb = cv2.inpaint(np.ascontiguousarray(rgba[:,:,:3]),mask,4,cv2.INPAINT_TELEA)
    blended = rgba.copy()
    strength = cv2.GaussianBlur(mask, (9,9),2.3).astype(np.float32)[...,None] / 255.
    blended[:,:,:3] = np.rint(rgba[:,:,:3]*(1-strength) + rgb*strength).astype('uint8')
    return Image.fromarray(blended,'RGBA')


def mouth_layer(image, target_width, angle):
    box = image.getbbox()
    if not box: raise ValueError('Blank viseme image')
    shape = image.crop(box)
    target_height = max(4,round(shape.height * target_width/shape.width))
    shape = shape.resize((target_width,target_height),Image.Resampling.LANCZOS)
    return shape.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def generate_visemes():
    OUT.mkdir(parents=True,exist_ok=True)
    for pose, c in CALIBRATION.items():
        original = Image.open(SRC / (pose+'.png')).convert('RGBA')
        # Preserve the original mouth on rests. The V3 'rest' falsely painted
        # a new, wider smile on top of the original mouth.
        original.save(OUT / (pose+'_rest.png'))
        skin = cleaned_skin(original,c['center'],c['cover'])
        for shape in V4_SHAPES:
            if shape=='rest': continue
            # The supplied O has a large flesh-coloured ring. A smaller open
            # mouth reads better at realistic head scale without that artifact.
            source_shape='open' if shape=='O' else shape
            mouth = Image.open(SRC / 'visemes' / (source_shape+'.png')).convert('RGBA')
            # Closed sounds keep the original design, not teeth pasted over lips.
            if shape == 'MBP':
                original.save(OUT / (pose+'_'+shape+'.png'))
                continue
            relative={'FV':.85,'L':.87,'AE':1.0,'O':.76,'UW':.75,'open':.93,'smile':.92}[shape]
            width=round(c['width']*relative)
            layer=mouth_layer(mouth,width,c['angle'])
            cx,cy=c['center']
            # Limit shift. Slightly lower for open vowels, to avoid appearing
            # attached to Evan's nose.
            yy=cy+(1 if shape in ('AE','open','O') else 0)
            left=round(cx-layer.width/2)
            top=round(yy-layer.height/2)
            result=skin.copy()
            result.alpha_composite(layer,(left,top))
            result.save(OUT/(pose+'_'+shape+'.png'))
    # Diagnostic metadata lets later calibration be updated systematically.
    import json
    (OUT/'calibration.json').write_text(json.dumps({'version':4,'poses':CALIBRATION,
                         'description':'Original V3 face for rests and calibrated original visemes for speech'},indent=2))


def generate_brand():
    BRAND.mkdir(parents=True,exist_ok=True)
    raw=Image.open(LOGO_SOURCE).convert('RGB')
    raw_arr=np.asarray(raw).astype(np.float32)
    luminance=raw_arr.min(axis=2)
    # Original source is black symbol on white. Reconstruct the alpha rather
    # than just treating the large white square as a logo background.
    alpha=np.clip((250-luminance)/240.,0,1)
    alpha[alpha<.018]=0
    a=np.rint(alpha*255).astype('uint8')
    y,x=np.nonzero(a>6)
    if len(x)==0: raise ValueError('Brand logo source had no visible pixels')
    bounds=(max(0,int(x.min())-4), max(0,int(y.min())-4),min(raw.width,int(x.max())+5), min(raw.height,int(y.max())+5))
    alpha_img=Image.fromarray(a,'L').crop(bounds)
    for name,color in [('rovor-mark-black.png',(12,18,27)),('rovor-mark-white.png',(255,255,255))]:
        out=Image.new('RGBA',alpha_img.size,(*color,0));out.putalpha(alpha_img)
        out.save(BRAND/name,optimize=True)
    raw.save(BRAND/'source-original.png',optimize=True)


if __name__=='__main__':
    generate_visemes()
    generate_brand()
    print('Created calibrated V4 mouth sprites and transparent original Rovor logo.')
