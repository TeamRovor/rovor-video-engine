"""Three editable FV source layers; runtime geometry/occlusion lives in code."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from fv_cartoon_head import FVContactHead

def export(output):
    head=FVContactHead();art={k:v.copy() for k,v in head.fv_layers.items()}
    head.fv_layers={k:np.zeros_like(v) for k,v in art.items()}
    skin=head.weights(np.eye(9)[7]);layers={'posed-skin-and-brows':skin,**{k:Image.fromarray(v) for k,v in art.items()}}
    psd=PSDImage.frompil(Image.new('RGBA',(512,512)))
    for name,im in layers.items():psd.create_pixel_layer(im,name=name)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output);opened=PSDImage.open(output)
    if [l.name for l in opened]!=list(layers):raise RuntimeError('FV PSD layer structure changed')
    im=opened.composite(force=True,ignore_preview=True).convert('RGBA');bg=Image.new('RGBA',im.size,'#f3eee2');bg.alpha_composite(im);bg.convert('RGB').save(output.with_suffix('.jpg'),quality=97)
    return dict(layers=list(layers),nativeMoho=False,note='Source assembly; runtime additionally warps and coarticulates layers')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.output)))
