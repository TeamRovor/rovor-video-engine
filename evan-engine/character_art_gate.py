"""Fail-closed mechanical gate for Evan's registered 2D character plates.

This never judges artistic appeal. A pass is proof of file integrity, separate
RGBA layers and shared registration only, NOT approval of acting/character art.
Use the approved cartoon design sheet and human visual review for that.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

SCHEMA_VERSION = 1
DIRECTION_ID = 'rovor-evan-expressive-cartoon'
WARDROBE = {
    'hair': 'dark-tousled', 'eyewear': 'sunglasses',
    'shirt': 'navy-collared-shirt', 'tie': 'black-tie',
}
REQUIRED_LAYERS = (
    'hair-back', 'hair-front', 'head-base', 'eyes', 'glasses',
    'brow-left', 'brow-right', 'jaw', 'oral-cavity', 'upper-teeth',
    'tongue', 'upper-lip', 'lower-lip', 'neck', 'torso', 'tie',
    'upper-arm-left', 'forearm-left', 'upper-arm-right', 'forearm-right',
    'hand-left-relaxed', 'hand-left-open', 'hand-left-point',
    'hand-right-relaxed', 'hand-right-open', 'hand-right-point',
)


def _located(root: Path, relative: str) -> Path:
    """No absolute paths, traversal, network or symlink escape in an art package."""
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Layer/source paths must be nonempty package-relative paths')
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('File escapes asset package root: ' + relative)
    if not path.is_file():
        raise ValueError('Missing source artwork: ' + relative)
    return path


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(128 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _pivot(pivot, width: int, height: int):
    if not isinstance(pivot, dict) or set(pivot) != {'x', 'y'}:
        raise ValueError('Each layer needs an explicit x/y pivot in shared-canvas pixels')
    x, y = pivot['x'], pivot['y']
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)):
        raise ValueError('Nonfinite pivot')
    if not (0 <= x <= width and 0 <= y <= height):
        raise ValueError('Pivot outside common stage')


def inspect(manifest: dict, root: Path) -> dict:
    """Return a mechanical report; malformed art fails instead of being promoted.

    Metadata wardrobe claims aren't checked from pixels: report that limitation.
    Every layer must be independently transparent and canvas-registered.
    """
    root = Path(root).resolve()
    if not isinstance(manifest, dict) or manifest.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError('Unsupported character-art manifest schema')
    if manifest.get('directionId') != DIRECTION_ID:
        raise ValueError('Rejected/superseded visual direction')
    if manifest.get('wardrobe') != WARDROBE:
        raise ValueError('Wardrobe/identity spec mismatch. No hoodies instead of navy shirt and black tie')
    canvas = manifest.get('canvas', {})
    w, h = canvas.get('width'), canvas.get('height')
    if not (isinstance(w, int) and isinstance(h, int) and 64 <= w <= 8192 and 64 <= h <= 8192):
        raise ValueError('One valid common registration canvas (64..8192 px) is required')
    design = manifest.get('sourceConcept')
    if not isinstance(design, dict) or not isinstance(design.get('sha256'), str):
        raise ValueError('Source design reference and SHA-256 must be recorded')
    concept = _located(root, design.get('path'))
    if _digest(concept) != design['sha256'].lower():
        raise ValueError('Source character reference checksum mismatch')
    layers = manifest.get('layers')
    if not isinstance(layers, dict) or set(layers) != set(REQUIRED_LAYERS):
        missing = sorted(set(REQUIRED_LAYERS) - set(layers or {}))
        extra = sorted(set(layers or {}) - set(REQUIRED_LAYERS))
        raise ValueError(f'Missing/extra independent character layers: missing={missing}, extra={extra}')
    seen = set()
    results = []
    for name in REQUIRED_LAYERS:
        entry = layers[name]
        if not isinstance(entry, dict) or not isinstance(entry.get('sha256'), str):
            raise ValueError('Every layer requires a SHA-256 and pivot: ' + name)
        rel = entry.get('path')
        if rel in seen:
            raise ValueError('Multiple layers point to the same flattened file: ' + str(rel))
        seen.add(rel)
        _pivot(entry.get('pivot'), w, h)
        path = _located(root, rel)
        if path.suffix.lower() != '.png':
            raise ValueError('Layer must be PNG with authored alpha, not RGB or JPEG: ' + name)
        if _digest(path) != entry['sha256'].lower():
            raise ValueError('Artwork changed without checksum update: ' + name)
        with Image.open(path) as im:
            if im.format != 'PNG' or im.mode != 'RGBA' or im.size != (w, h):
                raise ValueError('Layer must be a registered RGBA PNG on the common canvas: ' + name)
            alpha = im.getchannel('A')
            if alpha.getextrema() == (255, 255):
                raise ValueError('Opaque composite/background; alpha separation required: ' + name)
            # Ignore stray semi-transparent antialias pixels under 32 during silhouette test.
            mask = alpha.point(lambda px: 255 if px >= 32 else 0)
            bounds = mask.getbbox()
            if bounds is None:
                raise ValueError('Empty character plate: ' + name)
            x0, y0, x1, y1 = bounds
            if x0 <= 0 or y0 <= 0 or x1 >= w or y1 >= h:
                raise ValueError('Plate silhouette touches or clips the canvas: ' + name)
            nonempty_fraction = mask.histogram()[255] / (w * h)
            if nonempty_fraction > .72:
                raise ValueError('Likely flattened/composite plate covers too much stage: ' + name)
        results.append({'layer': name, 'bbox': bounds, 'occupiedFraction': round(nonempty_fraction, 5)})
    # Hand exposure variants must be different drawings registered to one wrist
    # for each side, not relabelled copies of the same silhouette.
    for side in ('left', 'right'):
        variants = [layers[f'hand-{side}-{pose}'] for pose in ('relaxed', 'open', 'point')]
        anchors = [(v['pivot']['x'], v['pivot']['y']) for v in variants]
        if len(set(anchors)) != 1:
            raise ValueError('Hand variants must share one wrist pivot: ' + side)
        if len({v['sha256'].lower() for v in variants}) != 3:
            raise ValueError('Hand pose variants cannot be identical image copies: ' + side)
    return {
        'schemaVersion': 1, 'directionId': DIRECTION_ID,
        'mechanicalStatus': 'passed', 'registeredLayerCount': len(results),
        'referenceSha256': design['sha256'].lower(), 'layerEvidence': results,
        'animationReady': False, 'visualApproved': False, 'releaseReady': False,
        'imageSemanticsVerified': False,
        'humanVisualReviewRequired': [
            'Appealing approved Evan design, exact wardrobe and source likeness cues',
            'Artist-inspected fingers, silhouette, hidden joints and profile poses',
            'Clean face/jaw and F/V, L, M/B/P at real delivery resolution',
            'Registered pivots and deformable components in a test Moho/2D animation scene',
            'Silent-acting readability and accurate real-audio normal-speed lip sync',
        ],
        'note': 'A wardrobe tag or passing geometry cannot verify image semantics. '
                'No automatic mechanism here can claim studio quality or art approval.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    report = inspect(json.loads(args.manifest.read_text()), args.manifest.parent)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('mechanicalStatus', 'registeredLayerCount', 'animationReady', 'visualApproved')}, indent=2))


if __name__ == '__main__':
    main()