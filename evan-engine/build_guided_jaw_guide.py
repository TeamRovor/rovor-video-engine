"""Draw construction guides only, not replacement lip/jaw artwork.

The fixed native work window is magnified4x for source generation. Pink top
interface and cyan jaw contour are authored proposals, not measured anatomy.
"""
from PIL import Image,ImageDraw
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();p=args.output;p.mkdir(parents=True,exist_ok=True)
# Exact work-window coordinates in native head space: no final artwork.
window=(128,288,384,448);scale=4
conv=lambda points:[((x-128)*scale,(y-288)*scale) for x,y in points]
upper=[(164,315),(181,320),(194,325),(211,327),(228.5,328.5),(246,327),(263,325),(298,321),(329,320)]
lower=[(329,320),(328,355),(304,360),(278,372),(245,389),(220,394),(195,391),(181,375),(164,335),(164,315)]
im=Image.new('RGBA',(1024,640));d=ImageDraw.Draw(im);d.line(conv(upper),fill=(220,40,110,255),width=3);d.line(conv(lower),fill=(0,110,130,255),width=3)
for x,y in [(194,325),(228.5,328.5),(263,325),(220,394),(164,315),(329,320)]:
 xx,yy=conv([(x,y)])[0];d.line((xx-8,yy,xx+8,yy),fill=(0,80,100,255),width=2);d.line((xx,yy-8,xx,yy+8),fill=(0,80,100,255),width=2)
im.save(p/'Release-Jaw-Guide.png')
bg=Image.new('RGBA',im.size,'#f3eee2');bg.alpha_composite(im);bg.convert('RGB').save(p/'Release-Jaw-Guide-Opaque.png')
