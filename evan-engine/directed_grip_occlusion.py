"""Original Evan's registered hand as a foreground pass over a held tool.

This improves real compositing depth at the grip: original actor body behind
the roller, original registered relaxed hand over the roller handle. It uses
the same calibrated right-arm FK, original WristPlate transform and body_roll
as CartoonBody.render -- never generative or replacement hand imagery.

The existing registered relaxed hand is experimental; rendering its pixels
in front of a tool does NOT prove anatomically correct wrapped fingers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image
from cartoon_wrist import WristPlate
from cartoon_body import ROOT
from right_hand_grip import ACTOR_SIZE


class ForegroundHand:
    """Reusable bounded last-frame cache shared by portrait/landscape scenes."""

    def __init__(self, rig_meta, hand_meta, root=ROOT):
        root=Path(root)
        if not isinstance(rig_meta,dict) or not isinstance(hand_meta,dict):
            raise ValueError("Actual source Evans's registered arm and hand manifests required")
        source=hand_meta.get("relaxed-right")
        if not isinstance(source,dict) or "right" not in rig_meta.get("arms",{}):
            raise ValueError("Original experimental relaxed-right source hand registration missing")
        filename=source.get("file")
        if (not isinstance(filename,str) or Path(filename).name!=filename
                or not filename.endswith(".png") or filename.startswith(".")):
            raise ValueError("Original source hand must use safe registered PNG filename")
        path=root/"hand-source"/filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("Original registered hand artwork absent")
        with Image.open(path) as src:
            if src.mode!="RGBA":
                raise ValueError("Original hand plate must have RGBA source alpha")
            hand=src.copy()
        geo={**rig_meta["arms"]["right"],
             "wrist":source.get("rigWrist",rig_meta["arms"]["right"]["wrist"])}
        self.plate=WristPlate(hand,source,geo)
        self.last_key=None
        self.last_image=None

    def image_at(self,frame,angles,body_roll):
        if (type(frame) is not int or frame<0
                or not isinstance(angles,(tuple,list)) or len(angles)!=3
                or any(type(a) not in (int,float) or not math.isfinite(a) for a in angles)
                or type(body_roll) not in (int,float) or not math.isfinite(body_roll)
                or abs(body_roll)>1.5):
            raise ValueError("Original right-hand foreground FK values invalid")
        key=(frame,tuple(angles),float(body_roll))
        if key!=self.last_key:
            part,(x,y)=self.plate.render(angles)
            actor=Image.new("RGBA",ACTOR_SIZE)
            actor.alpha_composite(part,(x+220,y))
            if body_roll:
                actor=actor.rotate(body_roll,Image.Resampling.BICUBIC,center=(732,950))
            if actor.getchannel("A").getbbox() is None:
                raise ValueError("Original foreground grip art has no visible hand pixels")
            self.last_key=key
            self.last_image=actor
        return self.last_image


def grip_foreground_rules(original_shot,controls,performance):
    """Trusted per-frame authored tool IDs, FK joint keys and original body roll.

    Each grip frame is prevalidated by right_hand_grip.solve_grips. No tool
    can be replaced by a different stroke or unrelated hand art at runtime.
    """
    original=original_shot.get("handGripConstraints",[])
    if not controls:
        return {}
    if performance is None:
        raise ValueError("Original FK performance required for foreground hand pass")
    table={}
    for rule in original:
        tool=rule["toolAssetId"]
        for frame in range(rule["startFrame"],rule["endFrameExclusive"]):
            if frame not in controls or frame in table:
                raise ValueError("Foreground tool grip frames must match solved original FK")
            acting=performance.at_frame(frame)
            if acting.get("right_hand")!="relaxed":
                raise ValueError("Foreground hand only supports actual relaxed-right original pose")
            table[frame]=(tool,controls[frame],acting["body_roll"])
    if set(table)!=set(controls):
        raise ValueError("Original hand compositing frames do not cover all verified grips")
    return table
