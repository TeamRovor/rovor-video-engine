"""Export actual editable oral pixel layers; does not claim a native Moho rig."""
import argparse,json
from pathlib import Path
from PIL import Image
from psd_tools import PSDImage
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1/oral-rig'

def export(root,output):
    psd=PSDImage.frompil(Image.new('RGBA',(512,512)))
    names=['face-skin','cavity-outline','upper-teeth','tongue','tongue-raised','closed-lips','fv-contact']
    for name in names:
        layer=psd.create_pixel_layer(Image.open(root/(name+'.png')),name=name)
        layer.visible=name not in ('tongue-raised','closed-lips','fv-contact')
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output)
    reopened=PSDImage.open(output)
    if [l.name for l in reopened]!=names:raise RuntimeError('PSD layer structure changed')
    reopened.composite().save(output.with_suffix('.png'))
    return dict(layers=names,canvas=list(reopened.size),status='editable source layers; runtime mesh is implemented separately')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--rig',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(export(a.rig,a.output)))
