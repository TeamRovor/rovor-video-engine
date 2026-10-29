"""Inspect actual alpha on opaque backdrops, without distorting source art.

Source is read only. Native-size light/dark composites are the review masters;
the overview uses aspect-preserving thumbnails. No color key or alpha cleanup.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from render_cartoon_head_study import font


def fitted(image,box):
    """Fit into a review cell without changing the drawing's proportions."""
    copy=image.copy()
    copy.thumbnail(box,Image.Resampling.LANCZOS)
    return copy


def inspect(source,output):
    output.mkdir(parents=True,exist_ok=True)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    im=Image.open(source).convert('RGBA');raw=np.asarray(im);alpha=raw[:,:,3]
    ys,xs=np.where(alpha>0)
    box=None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    result=dict(source=str(source),sourceSha256=before,size=list(im.size),visibleAlphaBox=box,
                nonzeroAlphaPixels=int(np.count_nonzero(alpha)),opaqueAlphaPixels=int(np.count_nonzero(alpha==255)),
                hiddenRgbPixelsAtZeroAlpha=int(np.count_nonzero((alpha==0)&np.any(raw[:,:,:3]!=0,axis=2))),
                sourceModified=False,previewAspectPreserved=True,nativeComposites={},
                limits='Hidden RGB is not visible paint. Review native composites at 100%; overview thumbnails preserve aspect. Source pixels and alpha are never changed.')
    sheet=Image.new('RGB',(1600,1100),'#f3eee2');d=ImageDraw.Draw(sheet)
    for x,name,label,color in [(15,'Light','Actual alpha / light backdrop','#f3eee2'),(545,'Dark','Actual alpha / dark backdrop','#405563')]:
        composite=Image.new('RGBA',im.size,color);composite.alpha_composite(im);composite=composite.convert('RGB')
        filename=f'Native-{name}-Composite.png';composite.save(output/filename)
        result['nativeComposites'][name]=dict(file=filename,size=list(composite.size))
        small=fitted(composite,(512,512));sheet.paste(small,(x+(512-small.width)//2,60+(512-small.height)//2))
        d.text((x+10,20),label,font=font(22),fill='#253c49')
        if box:
            crop=composite.crop((max(0,box[0]-6),max(0,box[1]-6),min(im.width,box[2]+6),min(im.height,box[3]+6)))
            ratio=min(500/crop.width,340/crop.height)
            crop=crop.resize((max(1,round(crop.width*ratio)),max(1,round(crop.height*ratio))),Image.Resampling.NEAREST)
            sheet.paste(crop,(x+(500-crop.width)//2,650+(340-crop.height)//2))
    mask=fitted(Image.fromarray(alpha).convert('RGB'),(512,512));sheet.paste(mask,(1075+(512-mask.width)//2,60+(512-mask.height)//2))
    d.text((1090,20),'Alpha only',font=font(22),fill='#253c49')
    d.text((20,600),'Visible bounds / nearest sampling (native masters saved separately)',font=font(23),fill='#253c49')
    d.text((20,1040),f'Visible alpha box: {box}; zero-alpha RGB ignored; no shape stretching',font=font(22),fill='#253c49')
    sheet.save(output/'Alpha-Preview.png')
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    (output/'Alpha-Audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(inspect(a.source,a.output),indent=2))
