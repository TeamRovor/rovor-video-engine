"""Opt-in local skin transition from the existing registered glasses-free plate."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from layered_cartoon_head import ROOT


def build(root=ROOT):
    old = root / 'eye-underlay-v3'
    source = root / 'eye-underlay-v1'
    original = np.array(Image.open(old / 'underlay.png').convert('RGBA'))
    meta = json.loads((source / 'manifest.json').read_text())
    raw = source / 'source/glasses-free-v1.png'
    registered = np.array(Image.open(raw).convert('RGBA').resize((512, 512), Image.Resampling.LANCZOS))
    registered = cv2.warpAffine(registered, np.array(meta['matrix'], np.float32), (512, 512), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT)
    registered[:, :, :3] = np.clip(registered[:, :, :3].astype(float) + meta['skinOffset'], 0, 255).astype('uint8')
    mask = np.zeros((512, 512), np.uint8)
    polygon = [(165,216),(170,208),(191,210),(214,212),(242,208),(263,198),(288,187),(309,197),(319,212),(327,231),(315,237),(250,235),(231,230),(214,233),(172,236)]
    cv2.fillPoly(mask, [np.array(polygon, np.int32)], 255)
    mask[(registered[:, :, 0] < 175) | (registered[:, :, 0] < registered[:, :, 1]*1.1) | (original[:, :, 3] < 255)] = 0
    # shortcut: authored skin ownership; inspect again if the source registration changes.
    weight = np.clip(cv2.distanceTransform(mask, cv2.DIST_L2, 5)/3, 0, 1)[:, :, None]
    result = original.copy()
    result[:, :, :3] = np.rint(registered[:, :, :3]*weight + original[:, :, :3]*(1-weight)).astype('uint8')
    assert np.array_equal(result[mask == 0], original[mask == 0])
    assert np.array_equal(result[:, :, 3], original[:, :, 3])
    assert np.array_equal(result[240:], original[240:])
    working = root / 'eye-underlay-v4'
    working.mkdir(exist_ok=True)
    Image.fromarray(result).save(working / 'underlay.png')
    Image.fromarray(mask).save(working / 'forehead-mask.png')
    (working / 'glasses.png').write_bytes((old / 'glasses.png').read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(sourceSha256=sha(raw), previousUnderlaySha256=sha(old/'underlay.png'), registration=meta['matrix'], skinOffset=meta['skinOffset'], polygon=polygon, featherPixels=3, changedPixels=int(np.any(result != original, axis=2).sum()), outsideMaskExact=True, alphaExact=True, below240Exact=True, glassesByteExact=True, newGeneratedArtwork=False, defaultChanged=False, animationAccepted=False)
    assert 0 < report['changedPixels'] < 6000
    (working / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    cv2.setNumThreads(1)
    print(json.dumps(build(), indent=2))
