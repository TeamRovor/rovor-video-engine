"""Experiment: split artist-approved Evan art into head, neck and body layers.

This creates overlapping PNG assets for independent head tilts in a native Moho
project or a future renderer. Original V3 art is NOT modified. Requires Pillow.
These are rigging inputs, not a finished native Moho .moho project.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps, ImageStat

# Native source-PNG coordinates. Soft masks overlap the original neck texture
# to prevent visible holes when the head rotates through a restrained range.
POSES = {
 "neutral": {
   "pivot":[283,275], "mouth":[282,179],
   "head":[(0,0),(438,0),(438,166),(404,170),(393,189),(379,221),(351,245),(317,260),(318,277),(295,294),(269,298),(245,284),(237,256),(209,239),(175,208),(161,178),(155,145),(0,145)],
   "neck":[(191,197),(312,207),(326,297),(231,319),(185,275)]
 },
 "point": {
   "pivot":[180,219], "mouth":[182,144],
   "head":[(0,0),(300,0),(300,102),(290,123),(265,155),(236,177),(213,192),(205,218),(188,238),(161,236),(143,215),(129,190),(111,173),(96,153),(89,128),(80,110),(0,106)],
   "neck":[(105,149),(221,158),(235,243),(131,251),(103,208)]
 },
 "present": {
   "pivot":[224,224], "mouth":[223,158],
   "head":[(0,0),(408,0),(408,98),(374,110),(343,143),(314,167),(281,188),(258,206),(257,226),(238,245),(201,250),(181,233),(171,209),(144,184),(129,162),(120,124),(0,103)],
   "neck":[(144,172),(283,178),(287,254),(168,263),(131,215)]
 }
}


def polygon_mask(size, points, softness=1.4):
    mask=Image.new("L",size)
    ImageDraw.Draw(mask).polygon(points,fill=255)
    return mask.filter(ImageFilter.GaussianBlur(softness))


def split_pose(image, geometry):
    source=image.convert("RGBA")
    alpha=source.getchannel("A")
    mask=polygon_mask(source.size,geometry["head"])
    neck=polygon_mask(source.size,geometry["neck"])
    head=source.copy()
    head.putalpha(ImageChops.multiply(alpha,mask))
    # Keep source neck texture under head; otherwise tilting creates holes.
    bodymask=ImageChops.lighter(ImageOps.invert(mask),neck)
    body=source.copy()
    body.putalpha(ImageChops.multiply(alpha,bodymask))
    return body,head


def render_layers(body,head,degrees,pivot):
    rotated=head.rotate(degrees,resample=Image.Resampling.BICUBIC,
                        center=tuple(pivot),expand=False)
    return Image.alpha_composite(body,rotated)


def build(source,destination):
    source,destination=Path(source),Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    manifest={"version":1,"format":"layered raster character","poses":{}}
    for name,geo in POSES.items():
        original=Image.open(source/(name+".png")).convert("RGBA")
        body,head=split_pose(original,geo)
        body.save(destination/(name+"_body.png"))
        head.save(destination/(name+"_head.png"))
        reconstructed=render_layers(body,head,0,geo["pivot"])
        delta=ImageChops.difference(original.convert("RGB"),
                                    reconstructed.convert("RGB"))
        mean_error=sum(ImageStat.Stat(delta).mean)/3
        if mean_error>3:
            raise RuntimeError(f"{name}: unexpectedly high reconstruction error {mean_error}")
        manifest["poses"][name]={
            "head_image":name+"_head.png",
            "body_image":name+"_body.png",
            "pivot":geo["pivot"],"mouth_anchor":geo["mouth"],
            "dimensions":list(original.size),
            "zero_tilt_rgb_mae":round(mean_error,4),
            "safe_tilt_degrees":[-3,3]}
    (destination/"manifest.json").write_text(json.dumps(manifest,indent=2))
    return manifest


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=Path(__file__).resolve().parent.parent/"evan-character"/"v3-assets")
    p.add_argument("--output",type=Path,default=Path(__file__).resolve().parent.parent/"evan-character"/"rig-layers")
    a=p.parse_args()
    print(json.dumps({name:config["zero_tilt_rgb_mae"] for name,config
           in build(a.source,a.output)["poses"].items()},indent=2))
