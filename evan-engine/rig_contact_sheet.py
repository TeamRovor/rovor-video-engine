"""Build one visual QA contact sheet for all original Evan layered head poses.

Use the sheet to *reject* rigs with neck gaps, duplicate edges, or face changes.
Passing code tests is not artistic approval. Requires Pillow.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from build_layered_character import build, render_layers


def contact_sheet(source, layers, output):
    output=Path(output)
    config=build(source,layers)
    labels=["left tilt","neutral","right tilt"]
    poses=list(config["poses"].items())
    W,H=310,338
    sheet=Image.new("RGB",(W*3,H*len(poses)),(235,237,240))
    d=ImageDraw.Draw(sheet)
    for row,(name,meta) in enumerate(poses):
        body=Image.open(Path(layers)/meta["body_image"]).convert("RGBA")
        head=Image.open(Path(layers)/meta["head_image"]).convert("RGBA")
        x,y=meta["mouth_anchor"]
        crop=(max(0,x-97),max(0,y-115),
              min(body.width,x+104),min(body.height,y+120))
        for column,degrees in enumerate((-3,0,3)):
            result=render_layers(body,head,degrees,meta["pivot"])
            bg=Image.new("RGBA",result.size,(249,247,243,255))
            bg.alpha_composite(result)
            view=bg.convert("RGB").crop(crop)
            view=ImageOps.contain(view,(W,300))
            xx=column*W+(W-view.width)//2
            yy=row*H
            sheet.paste(view,(xx,yy))
            d.text((column*W+8,yy+305),f"{name}: {labels[column]} ({degrees}°)",fill=(30,39,55))
    output.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(output,quality=93)
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    default_root=Path(__file__).resolve().parent.parent/"evan-character"
    p.add_argument("--source",type=Path,default=default_root/"v3-assets")
    p.add_argument("--layers",type=Path,default=default_root/"rig-layers")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    print(contact_sheet(a.source,a.layers,a.output))
