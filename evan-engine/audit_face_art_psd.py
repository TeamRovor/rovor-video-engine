"""Validate artist PSD planes; export to staging only, never to runtime.

Structural checks do not certify anatomy, correspondence, contact, occlusion or
performance. Hidden REFERENCE__/GUIDE__ layers are never exported as artwork.
"""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import BlendMode
from face_art_contract import SIZE,PLANES,POSES,required


def read_plane(layer):
    if layer.is_group():raise ValueError('Art must be an individual raster plane, not a group')
    image=layer.topil(apply_icc=False)
    if image is None:raise ValueError('Missing raster channels')
    if layer.opacity!=255 or layer.blend_mode!=BlendMode.NORMAL:
        raise ValueError('Art requires full layer opacity and normal blending; bake intended paint alpha into its pixels')
    if layer.has_mask() or layer.has_vector_mask() or layer.has_effects() or layer.has_clip_layers() or layer.clipping:
        raise ValueError('Bake masks, effects and clipping into a standalone painted plane before import')
    image=image.convert('RGBA');out=Image.new('RGBA',SIZE)
    if layer.left<0 or layer.top<0 or layer.left+image.width>SIZE[0] or layer.top+image.height>SIZE[1]:raise ValueError('Plane extends outside native canvas')
    out.paste(image,(layer.left,layer.top));return out


def audit(source,pose,staging=None):
    psd=PSDImage.open(source);issues=[];rows=[];images={};ignored=[]
    if psd.size!=SIZE:issues.append(f'Expected native 512x512 canvas, got {psd.size}')
    names=[l.name for l in psd]
    for n,c in Counter(names).items():
        if c>1:issues.append(f'Duplicate layer name: {n}')
    for layer in psd:
        name=layer.name
        if name.startswith(('REFERENCE__','GUIDE__')):
            ignored.append(name);continue
        if not name.startswith('ART__') or name[5:] not in PLANES:
            issues.append(f'Unrecognized layer: {name}');continue
        plane=name[5:]
        try:
            image=read_plane(layer);a=np.array(image)[:,:,3];nonzero=int(np.count_nonzero(a));solid=int(np.count_nonzero(a>=16))
            x0,y0,x1,y1=PLANES[plane];outside=a.copy();outside[y0:y1,x0:x1]=0;outside_count=int(np.count_nonzero(outside))
            if outside_count:issues.append(f'{plane}: {outside_count} visible-alpha pixels outside drawing envelope')
            if plane in required(pose) and solid<8:issues.append(f'{plane}: required paint is blank or insubstantial')
            rows.append(dict(plane=plane,visibleAlphaPixels=nonzero,substantialAlphaPixels=solid,outsideEnvelopePixels=outside_count,visibleInPSD=layer.visible));images[plane]=image
        except ValueError as error:issues.append(f'{plane}: {error}')
    for n in sorted(set(PLANES)-set(images)):issues.append(f'Missing or unreadable ART__{n}')
    exported=[]
    if staging is not None and not issues:
        # No partial files from failed validation, and no engine asset writes.
        staging=Path(staging)
        repo=Path(__file__).resolve().parent.parent
        if staging.resolve().is_relative_to(repo):raise ValueError('Staging exports must be outside the repository; runtime promotion is a separate review step')
        staging.mkdir(parents=True,exist_ok=True)
        for name in PLANES:
            dest=staging/f'{name}.png'
            if dest.exists():raise FileExistsError(f'Refuse overwrite: {dest}')
        for name,image in images.items():
            dest=staging/f'{name}.png';image.save(dest);exported.append(dict(file=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    return dict(source=str(source),sourceSha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),pose=pose,structuralPass=not issues,issues=issues,planes=rows,ignoredReferenceAndGuideLayers=ignored,exported=exported,animationReady=False,runtimeLoaded=False,limits='Pixel bounds/plane structure only. Manual anatomy, shared lip/jaw correspondence, contact/occlusion and voiced performance review remain mandatory.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('pose',choices=POSES);p.add_argument('report',type=Path);p.add_argument('--export-staging',type=Path);a=p.parse_args();r=audit(a.source,a.pose,a.export_staging);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(structuralPass=r['structuralPass'],issues=r['issues'],animationReady=False),indent=2));raise SystemExit(0 if r['structuralPass'] else 2)
