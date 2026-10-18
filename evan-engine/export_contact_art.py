"""Export registered source-space mouth parts for artist cleanup, not a face rig."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from cartoon_body import ROOT

def export(output,root=ROOT):
    layers={n:Image.open(root/'fv-rig-v2'/(n+'.png')).convert('RGBA') for n in ('lower-lip','lip-contact','upper-teeth')}
    psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=Image.new('RGBA',(512,512))
    for name,im in layers.items():psd.create_pixel_layer(im,name=name);expected.alpha_composite(im)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output);opened=PSDImage.open(output)
    assert [l.name for l in opened]==list(layers)
    actual=opened.composite(force=True,ignore_preview=True).convert('RGBA')
    arrays=[np.asarray(x).astype(float) for x in (expected,actual)]
    for a in arrays:a[:,:,:3]*=a[:,:,3:4]/255
    delta=float(np.abs(arrays[0]-arrays[1]).mean());assert delta<1
    report=dict(layers=list(layers),meanPremultipliedDifference=delta,coordinateSpace='registered source 512x512; not runtime jaw pose',nativeMoho=False)
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.output)))
