"""Strict, local-only visual-asset evidence for Rovor production storyboards.

Verifies actual original artwork files exist and match content hashes. This
rejects fictional "custom-1" names standing in for missing scenes. It cannot
certify aesthetic quality, layered deformation, commercial rights or animation.
"""
import hashlib
import json
from pathlib import Path
import re
from PIL import Image

ASSET_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
VALID_KIND = {"character", "prop", "environment", "illustration", "fx-layer"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PSD_SIGNATURE = b"8BPS"


def checked_file(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError("Asset path must be non-empty and relative")
    path=Path(relative)
    if ".." in path.parts or "." in path.parts:
        raise ValueError("Asset traversal is forbidden")
    root=Path(root).resolve()
    full=(root/path).resolve()
    if not full.is_relative_to(root) or full.is_symlink() or not full.is_file():
        raise ValueError("Asset is absent or outside the original-art root")
    return full


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for piece in iter(lambda:f.read(1024*1024),b""):
            h.update(piece)
    return h.hexdigest()


def check_source_artwork(registry, folder):
    if not isinstance(registry,dict) or registry.get("schemaVersion") != 1:
        raise ValueError("Missing supported asset registry schema")
    assets=registry.get("assets")
    if not isinstance(assets,dict) or not assets:
        raise ValueError("No real original scene assets registered")
    recorded={}
    distinct_paths=set()
    for key,entry in assets.items():
        if not isinstance(key,str) or not ASSET_ID.fullmatch(key):
            raise ValueError("Invalid scene artwork ID")
        if not isinstance(entry,dict) or entry.get("kind") not in VALID_KIND:
            raise ValueError("Invalid kind for "+key)
        if entry.get("provenance") != "rovor-original":
            raise ValueError("No unverifiable stock or generated replacement provenance: "+key)
        expected=entry.get("sha256","")
        if not isinstance(expected,str) or not SHA256.fullmatch(expected):
            raise ValueError("Missing full artwork SHA256 for "+key)
        path=checked_file(folder,entry.get("path"))
        if path in distinct_paths:
            raise ValueError("Several IDs point to one flattened artwork source")
        distinct_paths.add(path)
        if path.suffix.lower() != ".png":
            raise ValueError("Scene registry needs an actual exported PNG image: "+key)
        with path.open("rb") as f:
            if f.read(8) != PNG_SIGNATURE:
                raise ValueError("Fake image header: "+key)
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
                if image.width < 32 or image.height < 32:
                    raise ValueError("Scene illustration too small for an animated asset: "+key)
                if entry["kind"] != "environment":
                    if image.mode != "RGBA" or image.getchannel("A").getextrema() == (0,0):
                        raise ValueError("Character/prop must have a nonempty RGBA layer: "+key)
        except (OSError,SyntaxError) as exc:
            raise ValueError("Cannot decode actual scene image: "+key) from exc
        if sha256(path) != expected:
            raise ValueError("Artwork SHA256 changed: "+key)
        recorded[key]={"path":str(path),"kind":entry["kind"],"sha256":expected}
    return recorded


def inspect_storyboard(plan, registry, folder):
    """Structural audit + file provenance; intentionally no publish approval."""
    from quality_gate import audit
    base=audit(plan)
    errors=list(base["problems"])
    if not isinstance(plan,dict):
        return {"valid":False,"problems":["Storyboard is not an object"],
                "publicationApproved":False}
    try:
        duration=float(plan.get("durationSec",0))
    except (ValueError,TypeError):
        duration=0
    if duration < 30:
        errors.append("Production narration must be at least 30 seconds")
    try:
        assets=check_source_artwork(registry,folder)
    except (ValueError,TypeError,OSError) as exc:
        errors.append("Original art registry invalid: "+str(exc))
        assets={}
    missing=set()
    noncharacter=set()
    referenced=set()
    for i,shot in enumerate(plan.get("shots",[]),1):
        if not isinstance(shot,dict):
            continue
        ids=shot.get("originalAssetIds",[])
        if not isinstance(ids,list):
            errors.append(f"Shot {i}: invalid originalAssetIds")
            continue
        used=[]
        for key in ids:
            if not isinstance(key,str) or key not in assets:
                missing.add(str(key))
            else:
                used.append(key)
                referenced.add(key)
                if assets[key]["kind"] != "character":
                    noncharacter.add(key)
        if shot.get("kind") in ("action","visual-explainer","object-demo","metaphor"):
            if not any(assets[key]["kind"] != "character" for key in used):
                errors.append(f"Shot {i}: no registered illustrated prop/environment, only character claims")
    if missing:
        errors.append("Unregistered source artwork referenced: "+", ".join(sorted(missing)[:20]))
    if duration >= 240 and len(noncharacter)<10:
        errors.append("Long-form requires ten distinct physically present original props/environments")
    result={**base,"valid":not errors,"problems":errors,
            "registeredAssetCount":len(assets),"usedRegisteredAssetCount":len(referenced),
            "noncharacterArtworkCount":len(noncharacter),
            "actualMotionInspected":False,"phonemeTimingVerified":False,
            "releaseApproved":False,"publicationApproved":False,
            "artworkIntegrityChecked":bool(assets),
            "note":"Hash-matched original artwork exists, but acting, interpolation, 3/4 views and story quality need actual rendered-film review."}
    return result


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("storyboard",type=Path)
    p.add_argument("asset_registry",type=Path)
    p.add_argument("--report",type=Path)
    args=p.parse_args()
    plan=json.loads(args.storyboard.read_text())
    registry=json.loads(args.asset_registry.read_text())
    report=inspect_storyboard(plan,registry,args.asset_registry.parent)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__=="__main__":main()
