"""Authored neck backing guide, not final artwork or measured anatomy."""
from PIL import Image,ImageDraw
from pathlib import Path
import argparse
# Authored hidden top surplus; visible silhouette sampled from the current
# reference below the jaw. Outline only: not generated final artwork.
pts=[(211,348),(324,340),(329,395),(331,410),(328,425),(317,435),(301,445),(281,455),(267,460),(252,461),(238,455),(223,445),(218,435),(218,425),(215,410),(211,395)]
window=(176,320,352,488);conv=lambda ps:[((x-176)*5,(y-320)*5) for x,y in ps]
im=Image.new('RGBA',(880,840));d=ImageDraw.Draw(im);d.line(conv(pts+[pts[0]]),fill=(0,110,130,255),width=3)
for x,y in [(211,348),(324,340),(328,425),(252,461),(218,435)]:
 xx,yy=conv([(x,y)])[0];d.line((xx-8,yy,xx+8,yy),fill=(0,80,100,255),width=2);d.line((xx,yy-8,xx,yy+8),fill=(0,80,100,255),width=2)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();p=args.output;p.mkdir(parents=True,exist_ok=True);im.save(p/'Neck-Guide.png');bg=Image.new('RGBA',im.size,'#f3eee2');bg.alpha_composite(im);bg.convert('RGB').save(p/'Neck-Guide-Opaque.png')
