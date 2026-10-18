"""Fail-closed original art readiness for narrated Rovor 2D production.

A physical animation can be technically valid and still look like a slideshow.
This gate prevents that technical success from being silently promoted to an
artist-approved character animation. It cannot *judge beauty*; the actual
character design, pose acting, silhouettes and inbetweens require human review.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image

PRODUCTION_POSES = ('anticipation', 'low_contact', 'midstroke',
                    'high_reach', 'overlap_pass', 'release', 'settle')
REQUIRED_LAYER_TYPES = ('head', 'torso', 'upper_arm', 'forearm', 'working_hand', 'legs')


def _sha(path):
    d = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(128*1024),b''):
            d.update(part)
    return d.hexdigest()


def _safe_file(root, relative):
    if not isinstance(relative,str) or not relative or relative.startswith('/'):
        return None
    folder = root.resolve()
    p = (folder/relative).resolve()
    if not p.is_relative_to(folder) or not p.is_file():
        return None
    return p


def inspect_art(manifest, root):
    """Assess files and explicitly recorded human review. Never auto-approve."""
    root = Path(root)
    issues=[]
    if manifest.get('kind')!='rovor-layered-cartoon-pose-package-v1':
        issues.append('Unsupported pose-package format')
    if manifest.get('style')!='original-2d-illustration':
        issues.append('Original 2D art provenance not recorded')
    if manifest.get('characterRole') not in ('secondary-painter','original-evan'):
        issues.append('Character source identity missing')
    views = manifest.get('sourceViews') or []
    if not isinstance(views,list) or 'working-three-quarter' not in views:
        issues.append('Missing original three-quarter working pose view')
    required = manifest.get('requiredPoseIds')
    if required!=list(PRODUCTION_POSES):
        issues.append('Seven directed performance beats must be explicitly covered')
    poses = manifest.get('poses')
    if not isinstance(poses,dict):
        poses={}
        issues.append('Pose registry missing')
    hashes={}
    verified_count=0
    for name in PRODUCTION_POSES:
        pose=poses.get(name)
        if not isinstance(pose,dict):
            issues.append(f'{name}: missing complete drawn pose')
            continue
        layers=pose.get('layerTypes')
        if not isinstance(layers,list) or not set(REQUIRED_LAYER_TYPES).issubset(set(map(str,layers))):
            issues.append(f'{name}: missing independent facial, body and hand layers')
        file = _safe_file(root,pose.get('preview'))
        if not file:
            issues.append(f'{name}: missing safe registered drawing')
            continue
        expected = pose.get('sha256')
        digest = _sha(file)
        if not isinstance(expected,str) or digest!=expected:
            issues.append(f'{name}: source artwork fingerprint mismatch')
            continue
        try:
            with Image.open(file) as img:
                if img.mode!='RGBA' or max(img.size)<700:
                    raise ValueError('native transparent registered artwork is required')
                low,high=img.getchannel('A').getextrema()
                if low>=255 or high<=0:
                    raise ValueError('transparent nonempty artwork required')
        except Exception as err:
            issues.append(f'{name}: invalid layered preview: {err}')
            continue
        if digest in hashes:
            issues.append(f'{name}: duplicated visual pose from {hashes[digest]}')
            continue
        hashes[digest]=name
        verified_count+=1
    layouts=manifest.get('layouts') or {}
    for orientation in ('landscape','portrait'):
        comp=layouts.get(orientation)
        if not isinstance(comp,dict) or not comp.get('independentShotComposition'):
            issues.append(f'{orientation}: requires independently staged shot review')
    review = manifest.get('humanVisualReview') or {}
    if (review.get('artApproved') is not True or
        not isinstance(review.get('reviewerEvidence'),str) or
        len(review.get('reviewerEvidence','').strip())<16):
        issues.append('Artist-directed visual review has not approved the source poses')
    if review.get('performanceInMotionApproved') is not True:
        issues.append('Human normal-speed movement review not approved')
    return {
        'status':'ART_READY_FOR_FINAL_RENDER' if not issues else 'ART_NOT_READY',
        'verifiedUniquePoseCount':verified_count,
        'expectedPoseCount':len(PRODUCTION_POSES),
        'ready':not issues,
        'problems':issues,
        'noAutomaticStudioQualityCertification':True,
        'publicationApproved':False,
    }


def require_art_ready(manifest,root):
    result=inspect_art(manifest,root)
    if not result['ready']:
        raise ValueError('Art-gate rejected: '+ '; '.join(result['problems'][:5]))
    return result


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('manifest',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--strict',action='store_true')
    a=p.parse_args()
    data=json.loads(a.manifest.read_text())
    r=inspect_art(data,a.manifest.parent)
    if a.out:
        a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
    if a.strict and not r['ready']:
        raise SystemExit(2)

if __name__=='__main__':main()