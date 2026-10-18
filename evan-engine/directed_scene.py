"""Directed original-art scene composition for the Rovor 2D animation engine.

Not a generative image tool. Animates real registered illustrated PNG layers and
the actual layered Evan frame. For 30-900s narration, shots have independent
1920x1080 and 1080x1920 compositions, authored camera moves, prop acting and
foreground occlusion. No placeholders or unrelated filler scenes.

This module supplies deterministic frame production; aesthetic judgment,
script relevance and exact English phoneme alignment still require review.
"""
from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageColor

SIZES={"landscape":(1920,1080),"portrait":(1080,1920)}
FPS=60
ACTOR_ID="original-evan-rig"
ALLOWED_ROLES={"background","prop","character","foreground","atmosphere"}
CHANNELS={"x":(0,1),"y":(0,1),"scale":(.05,3.5),"rotation":(-35,35),"opacity":(0,1)}
CAMERA={"panX":(-.35,.35),"panY":(-.35,.35),"zoom":(.8,1.65)}
MAX_STILL_SECONDS=9


def finite(v,key,low,high):
    if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not low<=v<=high:
        raise ValueError("Invalid "+key+"; expected "+str((low,high)))
    return float(v)


def parse_keys(keys,begin,end,bounds):
    if not isinstance(keys,list) or len(keys)<2:
        raise ValueError("Requires two or more scene/camera keyframes")
    frames=[]
    out=[]
    for row in keys:
        if not isinstance(row,dict):
            raise ValueError("Invalid keyframe")
        frame=row.get("frame")
        if isinstance(frame,bool) or not isinstance(frame,int) or not begin<=frame<=end:
            raise ValueError("Invalid global scene frame")
        if frames and frame<=frames[-1]:
            raise ValueError("Keyframes must be strictly increasing")
        if row.get("ease","smooth") not in ("smooth","linear","hold"):
            raise ValueError("Unsupported interpolation")
        values={k:finite(row.get(k),k,*limit) for k,limit in bounds.items()}
        out.append((frame,values,row.get("ease","smooth")))
        frames.append(frame)
    if frames[0]!=begin or frames[-1]!=end:
        raise ValueError("Animation must cover exact scene interval including boundary")
    return out


def interpolate(keys,frame):
    positions=[row[0] for row in keys]
    i=max(0,bisect_right(positions,frame)-1)
    prev=keys[i]
    if i==len(keys)-1:return dict(prev[1])
    nxt=keys[i+1]
    u=(frame-prev[0])/(nxt[0]-prev[0])
    if prev[2]=="hold":u=0.
    elif prev[2]=="smooth":u=u*u*(3-2*u)
    return {key:value+(nxt[1][key]-value)*u for key,value in prev[1].items()}


def checked_path(root,name):
    if not isinstance(name,str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Invalid registered image path")
    root=Path(root).resolve()
    path=(root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ValueError("Missing original scene art")
    return path


def open_artwork(registry,root):
    if registry.get("schemaVersion")!=1:
        raise ValueError("Source art manifest required")
    assets=registry.get("assets",{})
    if not isinstance(assets,dict):
        raise ValueError("Invalid original art manifest")
    opened={}
    for aid,meta in assets.items():
        if meta.get("provenance")!="rovor-original":
            raise ValueError("External/stolen or unknown image art disallowed")
        file=checked_path(root,meta.get("path"))
        if file.suffix.lower()!=".png":
            raise ValueError("Only source-verified transparent PNGs are supported")
        digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if digest!=meta.get("sha256"):
            raise ValueError("Source art integrity mismatch")
        with Image.open(file) as im:
            im.verify()
        with Image.open(file) as im:
            opened[aid]=im.convert("RGBA")
        if min(opened[aid].size)<32:
            raise ValueError("Source illustration too small")
    return opened


def check(config,registry,root):
    if not isinstance(config,dict) or config.get("schemaVersion")!=1:
        raise ValueError("Directed scene file required")
    duration=finite(config.get("durationSec"),"durationSec",30,900)
    total=math.ceil(duration*FPS-1e-9)
    shots=config.get("shots")
    if not isinstance(shots,list) or not shots:
        raise ValueError("No directed animated scenes")
    images=open_artwork(registry,root)
    cursor=0
    ready=[]
    seen=set()
    for index,shot in enumerate(shots,1):
        begin,end=shot.get("startFrame"),shot.get("endFrameExclusive")
        if (isinstance(begin,bool) or isinstance(end,bool) or not isinstance(begin,int)
            or not isinstance(end,int) or begin!=cursor or end<=begin or end>total):
            raise ValueError("Scene gap, overlap, or invalid frame interval")
        cursor=end
        if end-begin>15*FPS:
            raise ValueError("Unacceptably long single-shot stage")
        if not isinstance(shot.get("visualPurpose"),str) or len(shot["visualPurpose"].strip())<18:
            raise ValueError("Missing original narrative/physical scene purpose")
        if not isinstance(shot.get("actionPayoff"),str) or len(shot["actionPayoff"].strip())<12:
            raise ValueError("Shot must create a visual development/payoff")
        compositions={}
        for view in SIZES:
            comp=shot.get("compositions",{}).get(view)
            if not isinstance(comp,dict):
                raise ValueError("Both landscape and portrait require unique compositions")
            fill=comp.get("background","#f3f0e8")
            try:
                ImageColor.getrgb(fill)
            except (ValueError,TypeError):
                raise ValueError("Bad stage background color")
            camera=parse_keys(comp.get("camera"),begin,end,CAMERA)
            elements=comp.get("elements")
            if not isinstance(elements,list) or not elements:
                raise ValueError("Directed shot lacks illustrated elements")
            processed=[]
            motion_score=0.
            non_actor_motion=0.
            has_actor=False
            for layer in elements:
                if not isinstance(layer,dict) or layer.get("role") not in ALLOWED_ROLES:
                    raise ValueError("Invalid original art layer")
                aid=layer.get("assetId")
                if aid!=ACTOR_ID and aid not in images:
                    raise ValueError("Unregistered original illustration referenced")
                if aid==ACTOR_ID:
                    has_actor=True
                seen.add(aid)
                keys=parse_keys(layer.get("keys"),begin,end,CHANNELS)
                delta=sum(abs(keys[-1][1][k]-keys[0][1][k]) for k in ("x","y","scale","rotation"))
                motion_score+=delta
                if aid!=ACTOR_ID:non_actor_motion+=delta
                processed.append({"assetId":aid,"role":layer["role"],"keys":keys})
            cam_delta=sum(abs(camera[-1][1][k]-camera[0][1][k]) for k in CAMERA)
            if end-begin>MAX_STILL_SECONDS*FPS and non_actor_motion<.07 and cam_delta<.06:
                raise ValueError("Extended inert talking scene: add meaningful illustrated action")
            if shot.get("kind") in ("action","object-demo","visual-explainer") and non_actor_motion<.035:
                raise ValueError("An action scene must actually animate original illustrated props")
            compositions[view]={"background":fill,"camera":camera,
                                "elements":processed,"hasActor":has_actor}
        ready.append({"startFrame":begin,"endFrameExclusive":end,
                      "kind":shot.get("kind"),"visualPurpose":shot["visualPurpose"],
                      "actionPayoff":shot["actionPayoff"],"compositions":compositions})
    if cursor!=total:
        raise ValueError("Directed scenes do not cover full original narration")
    return {"durationSec":duration,"totalFrames":total,"scenes":ready,
            "artwork":images,"distinctAssetIds":len(seen),"creativeApproved":False}


class DirectedScene:
    def __init__(self,config,registry,artroot,portrait=False):
        result=check(config,registry,artroot)
        self.scenes=result["scenes"]
        self.images=result["artwork"]
        self.view="portrait" if portrait else "landscape"
        self.size=SIZES[self.view]
        self.ends=[shot["endFrameExclusive"] for shot in self.scenes]

    def frame(self,index,evan=None):
        i=bisect_right(self.ends,index)
        if i>=len(self.scenes):raise ValueError("Frame beyond narrated scene")
        shot=self.scenes[i]
        if index<shot["startFrame"]:raise ValueError("Frame before narrated scene")
        view=shot["compositions"][self.view]
        w,h=self.size
        stage=Image.new("RGBA",self.size,view["background"])
        camera=interpolate(view["camera"],index)
        for item in view["elements"]:
            aid=item["assetId"]
            src=evan if aid==ACTOR_ID else self.images[aid]
            if src is None:
                raise ValueError("Missing actual layered Evan RGBA frame")
            if src.mode!="RGBA":src=src.convert("RGBA")
            k=interpolate(item["keys"],index)
            zoom=camera["zoom"]
            width=max(2,round(src.width*k["scale"]*zoom))
            height=max(2,round(src.height*k["scale"]*zoom))
            if width>5000 or height>5000:
                raise ValueError("Artwork scale exceeds safe bounds")
            layer=src.resize((width,height),Image.Resampling.BILINEAR)
            if abs(k["rotation"])>1e-6:
                layer=layer.rotate(-k["rotation"],Image.Resampling.BICUBIC,expand=True)
            if k["opacity"]<1:
                alpha=layer.getchannel("A").point(lambda a:round(a*k["opacity"]))
                layer.putalpha(alpha)
            x=round((k["x"]-.5)*w*zoom+w*(.5-camera["panX"]))
            y=round((k["y"]-.5)*h*zoom+h*(.5-camera["panY"]))
            stage.alpha_composite(layer,(x-layer.width//2,y-layer.height//2))
        return stage.convert("RGB")
