"""Editable canonical F/V construction layers, not a native/full character rig."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from layered_cartoon_head import ROOT,over
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=np.zeros((512,512,4),np.float32)
    names=['lip-contact','upper-teeth']
    for n in names:
        im=Image.open(ROOT/'fv-rig-v3'/f'{n}.png').convert('RGBA');psd.create_pixel_layer(im,name=n);raw=np.asarray(im).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255;expected=over(expected,raw)
    a.output.parent.mkdir(parents=True,exist_ok=True);psd.save(a.output);reopened=PSDImage.open(a.output);assert [l.name for l in reopened]==names
    im=reopened.composite(ignore_preview=True).convert('RGBA');im.save(a.output.with_suffix('.png'));raw=np.asarray(im).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255;error=float(abs(raw-expected).mean());assert error<.1
    report=dict(layers=names,canvas=[512,512],meanPremultipliedDifference255=error,status='Canonical F/V source placement; runtime uniform parent and timing remain separate; not Moho')
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
