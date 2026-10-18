"""Two actual registered oral-art layers at E source geometry, not Moho."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from layered_cartoon_head import ROOT,over

def export(output,root=ROOT):
    psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=np.zeros((512,512,4),np.float32)
    for name in ['cavity','rim']:
        art=Image.open(root/f'round-rig-v1/{name}.png').convert('RGBA');psd.create_pixel_layer(art,name=name)
        p=np.asarray(art).astype('float32');p[:,:,:3]*=p[:,:,3:4]/255;expected=over(expected,p)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output);reopened=PSDImage.open(output)
    assert [l.name for l in reopened]==['cavity','rim']
    composite=reopened.composite(ignore_preview=True).convert('RGBA');composite.save(output.with_suffix('.png'))
    actual=np.asarray(composite).astype('float32');actual[:,:,:3]*=actual[:,:,3:4]/255
    error=float(abs(actual-expected).mean())
    if error>.1:raise RuntimeError(f'PSD pixel mismatch {error}')
    return dict(layers=['cavity','rim'],canvas=[512,512],meanPremultipliedDifference255=error,status='registered source-space E construction plate; runtime mesh, teeth/tongue and timing are separate')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.output),indent=2))
