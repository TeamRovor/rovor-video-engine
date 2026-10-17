"""Verifies the user's *actual* Rovor autonomous rover references.

An all-view reference board and a side hero are NOT a registered 3D model.
Validating exact bytes does not approve any generated replacement or cartoon rig.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image

EXPECTED_IDS=frozenset(('rovor-left-right-and-top','rovor-side-hero'))


def inspect_references(manifest,root):
    if manifest.get('schemaVersion')!=1 or manifest.get('assetCategory')!='rovor-autonomous-rover':
        raise ValueError('Expected Rovor autonomous rover source manifest')
    rows=manifest.get('references')
    if not isinstance(rows,list) or {r.get('id') for r in rows}!=EXPECTED_IDS or len(rows)!=2:
        raise ValueError('Both verified original reference views required')
    root=Path(root).resolve()
    verified=[]
    for ref in rows:
        name=ref.get('filename')
        if not isinstance(name,str) or Path(name).name!=name:
            raise ValueError('Only local basename source images supported')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Missing exact source reference: '+name)
        data=path.read_bytes()
        sha=hashlib.sha256(data).hexdigest()
        if sha!=ref.get('sha256'):
            raise ValueError('Reference changed: '+name)
        with Image.open(path) as image:
            width,height=image.size
            if image.format!='PNG' or [width,height]!=ref.get('pixels'):
                raise ValueError('Image dimensions or format changed: '+name)
        verified.append({'id':ref['id'],'sha256':sha,'pixels':[width,height]})
    return {'exactReferenceImagesVerified':True,'sourceViews':verified,
            'productionAssetApproved':False,'registeredModelAvailable':False,
            'cartoonRigReady':False,
            'notes':'Two images show source silhouette and branding; they do not include CAD geometry, layers, or a 3D mesh'}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('asset_dir',type=Path)
    a=p.parse_args(); print(json.dumps(inspect_references(json.loads(a.manifest.read_text()),a.asset_dir),indent=2))