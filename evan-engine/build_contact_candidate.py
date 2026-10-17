"""Register an isolated generated F/V drawing without replacing original art."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'


def build(root=ROOT):
    source=root/'oral-source/fv-contact-v2-source.png'
    drawing=Image.open(source).convert('RGBA')
    # Ignore isolated near-invisible generation residue when locating the art.
    bbox=drawing.getchannel('A').point(lambda v:255 if v>=8 else 0).getbbox()
    if bbox is None:raise ValueError('Empty contact drawing')
    plate=Image.new('RGBA',(512,512))
    plate.alpha_composite(drawing.crop(bbox).resize((90,27),Image.Resampling.LANCZOS),(194,311))
    target=root/'oral-rig/fv-contact-v2.png';plate.save(target)
    report={'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'sourceBounds':bbox,'targetBounds':[194,311,284,338],
            'outputSha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'status':'experimental alternative; inspect labiodental contact in motion',
            'visualApproved':False,'phonemeCorrectnessVerified':False}
    (root/'oral-rig/fv-contact-v2.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(build(),indent=2))
