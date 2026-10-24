"""Export actual editable painted character layers; no Moho launch is required."""
import argparse,json
from pathlib import Path
from PIL import Image
from psd_tools import PSDImage
from painted_character import PaintedCharacter


def export(root,output):
    root,output=Path(root),Path(output);c=PaintedCharacter(root)
    psd=PSDImage.frompil(Image.new('RGBA',(1464,1536),(0,0,0,0)))
    pad=220
    psd.create_pixel_layer(c.torso,name='Body - hidden shoulder plate',top=0,left=pad)
    arms=psd.create_group(name='Arms - bind mesh using manifest joint coordinates')
    for name in ('left','right'):
        arms.create_pixel_layer(Image.open(root/f'arm-{name}.png'),name=name.title()+' arm - shoulder elbow wrist skin',top=0,left=pad)
    heads=psd.create_group(name='Head drawings - X visible; switch or morph alternatives')
    trans=c.meta['head_transform'];x,y=trans['translate'];size=round(418*trans['scale'])
    for s in reversed(c.meta['face_order']):
        head=c.face(s,s,1).resize((size,size),Image.Resampling.LANCZOS)
        layer=heads.create_pixel_layer(head,name=s,top=y,left=x+pad);layer.visible=s=='X'
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output)
    reopened=PSDImage.open(output)
    actual=[(l.name,len(l) if l.is_group() else None) for l in reopened]
    if len(reopened)!=3 or len(reopened[1])!=2 or len(reopened[2])!=9:
        raise RuntimeError('Layered PSD round-trip did not preserve structure')
    comp=reopened.composite()
    if comp is None:raise RuntimeError('PSD has no composite preview')
    comp.save(output.with_suffix('.png'))
    return {'file':str(output),'canvas':list(reopened.size),'layers':actual,'pixel_layers':12}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rig',type=Path,default=Path(__file__).resolve().parent.parent/'evan-character/painted-v1/rig');p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(export(a.rig,a.output)))
