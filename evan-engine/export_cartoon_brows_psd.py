"""Three real pixel layers for brow construction, not native animation bones."""
import argparse,json
from pathlib import Path
from PIL import Image
from psd_tools import PSDImage
from cartoon_body import ROOT

def export(output,root=ROOT):
    names=['browless-head','brow-left','brow-right'];psd=PSDImage.frompil(Image.new('RGBA',(512,512)))
    for name in names:psd.create_pixel_layer(Image.open(root/'expression-rig'/(name+'.png')).convert('RGBA'),name=name)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output);opened=PSDImage.open(output)
    if [l.name for l in opened]!=names:raise RuntimeError('Brow PSD layer structure changed')
    im=opened.composite(force=True,ignore_preview=True).convert('RGBA');bg=Image.new('RGBA',im.size,'#f3eee2');bg.alpha_composite(im);bg.convert('RGB').save(output.with_suffix('.jpg'),quality=97)
    return dict(layers=names,nativeMoho=False,note='Runtime additionally applies hair/glasses occlusion to moved brows')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.output)))
