"""Four registered oral pixel layers at H geometry; not a native Moho rig."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from psd_tools import PSDImage
from cartoon_head import POINTS,warp
from layered_cartoon_head import ROOT,over,straight

def export(output,root=ROOT):
    cavity=warp(np.asarray(Image.open(root/'oral-rig/cavity-outline.png')),POINTS['C'],POINTS['H'],2)
    interior=cv2.erode(np.clip(cavity[:,:,3],0,255),np.ones((3,3),np.uint8))[:,:,None]/255
    layers=[('cavity',cavity)]
    for name in ['root-floor','blade']:
        layers.append((name,warp(np.asarray(Image.open(root/f'tongue-rig/{name}.png')),POINTS['H'],POINTS['H'],2)*interior))
    layers.append(('upper-teeth',warp(np.asarray(Image.open(root/'oral-rig/upper-teeth.png')),POINTS['C'],POINTS['H'],2)*interior))
    psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=np.zeros((512,512,4),np.float32)
    for name,art in layers:
        pixels=np.clip(straight(art),0,255).astype('uint8')
        psd.create_pixel_layer(Image.fromarray(pixels),name=name)
        quantized=pixels.astype('float32');quantized[:,:,:3]*=quantized[:,:,3:4]/255
        expected=over(expected,quantized)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output)
    reopened=PSDImage.open(output);assert [l.name for l in reopened]==[n for n,_ in layers]
    composite=reopened.composite(ignore_preview=True).convert('RGBA');composite.save(output.with_suffix('.png'))
    actual=np.asarray(composite).astype('float32');actual[:,:,:3]*=actual[:,:,3:4]/255
    error=float(np.abs(actual-expected).mean())
    if error>.1:raise RuntimeError(f'PSD compositing mismatch: {error}')
    return dict(layers=[n for n,_ in layers],canvas=[512,512],meanPremultipliedError255=error,status='registered oral construction plate; runtime head mesh and visibility are separate')

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.output),indent=2))
