"""Two actual tongue construction layers at H source geometry, before lip matte."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from psd_tools import PSDImage
from rooted_floor_cartoon_head import RootedFloorCartoonHead,rooted_blade_matrix
from cartoon_head import POINTS
from layered_cartoon_head import ROOT,straight,over
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--lift',type=float,choices=[0.,1.],default=1.);a=p.parse_args();head=RootedFloorCartoonHead();w=np.eye(9)[0]*(1-a.lift)+np.eye(9)[8]*a.lift;blade,floor=head.tongue_parts(w,POINTS['H']);layers=[('blade',blade),('root-floor',floor)];psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=np.zeros((512,512,4),np.float32)
    for name,art in layers:
        pixels=np.clip(straight(art),0,255).astype('uint8');psd.create_pixel_layer(Image.fromarray(pixels),name=name);v=pixels.astype('float32');v[:,:,:3]*=v[:,:,3:4]/255;expected=over(expected,v)
    a.output.parent.mkdir(parents=True,exist_ok=True);psd.save(a.output);reopened=PSDImage.open(a.output);assert [l.name for l in reopened]==['blade','root-floor'];im=reopened.composite(ignore_preview=True).convert('RGBA');im.save(a.output.with_suffix('.png'));actual=np.asarray(im).astype('float32');actual[:,:,:3]*=actual[:,:,3:4]/255;difference=abs(actual-expected);local=expected[:,:,3]>0;error=float(difference.mean());assert error<.1
    report=dict(layers=['blade','root-floor'],canvas=[512,512],sourceGeometry='H before lip/interior matte',lift=a.lift,matrix=rooted_blade_matrix(a.lift).tolist(),rootAnchor=[237,354],meanPremultipliedDifference255=error,localSupportMeanPremultipliedDifference255=float(difference[local].mean()),sourceSha256={n:hashlib.sha256((ROOT/f'tongue-rig/{n}.png').read_bytes()).hexdigest() for n in ['blade','root-floor']},status='Registered two-part construction; runtime oral mesh, lip/teeth masking, other head/body layers and timing remain separate. Not a native Moho rig or anatomical model.')
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
