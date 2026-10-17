"""Bounded registered shoulder repair and lower-neck overlap cleanup.

Original plates remain intact; a passing registration does not approve art.
"""
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from build_cartoon_body import ROOT,register_body


def build(root=ROOT):
    master=Image.open(root/'source/setup-v1.png').convert('RGBA')
    candidate=root/'body-source/armpit-cleanup-v2.png'
    registered,registration=register_body(master,Image.open(candidate).convert('RGBA'))
    original=Image.open(root/'body-rig/torso.png').convert('RGBA')
    raw=np.asarray(original).copy();replacement=np.asarray(registered).copy()
    mask=Image.new('L',original.size)
    draw=ImageDraw.Draw(mask)
    for box in ((334,455,404,548),(620,455,690,548)):
        draw.rounded_rectangle(box,radius=12,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(2))
    weight=np.asarray(mask).astype('float32')/255
    # The generated candidate is on a cream matte. Only navy/ink regions are
    # retained; the original alpha limits all changes to its existing surface.
    brightness=replacement[:,:,:3].max(axis=2).astype('float32')
    foreground=np.clip((220-brightness)/70,0,1)
    replacement[:,:,3]=(raw[:,:,3]*foreground).astype('uint8')
    output=raw.astype('float32')*(1-weight[:,:,None])+replacement.astype('float32')*weight[:,:,None]
    # Replace the residual chin colors with registered neck skin. Keep the
    # original alpha and collar: cutting the whole upper row created a notch.
    neck_source=root/'body-source/neck-cleanup-v3.png'
    neck_art,neck_registration=register_body(master,Image.open(neck_source).convert('RGBA'))
    neck=Image.new('L',original.size)
    ImageDraw.Draw(neck).polygon([(450,301),(568,301),(568,322),(544,358),(513,383),(480,360),(456,328)],fill=255)
    neck=neck.filter(ImageFilter.GaussianBlur(1))
    neck_weight=np.asarray(neck).astype('float32')/255
    neck_weight[np.indices(weight.shape)[0]>=340]=0
    skin=(raw[:,:,0].astype(float)>raw[:,:,1]*1.15)&(raw[:,:,1].astype(float)>=raw[:,:,2]*.95)
    neck_weight*=skin
    output[:,:,:3]=output[:,:,:3]*(1-neck_weight[:,:,None])+np.asarray(neck_art)[:,:,:3]*neck_weight[:,:,None]
    target=root/'body-rig/torso-cleanup-v2.png'
    Image.fromarray(np.clip(output,0,255).astype('uint8')).save(target)
    report={'registration':registration,'sourceSha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
            'originalSha256':hashlib.sha256((root/'body-rig/torso.png').read_bytes()).hexdigest(),
            'outputSha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'patchBoxes':[[334,455,404,548],[620,455,690,548]],
            'neckRegistration':neck_registration,
            'neckSourceSha256':hashlib.sha256(neck_source.read_bytes()).hexdigest(),
            'neckAlphaPreserved':True,'visualApproved':False,
            'status':'registered local repair candidate; inspect moving shoulder and neck overlaps'}
    (root/'body-rig/cleanup-v2.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(build(),indent=2))
