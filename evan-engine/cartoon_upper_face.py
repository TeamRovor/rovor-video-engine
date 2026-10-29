"""Opt-in registered upper face, original brows and independently lowered glasses.

Consumes a completed separated speech face; never edits its oral geometry.
"""
import json
import cv2
import numpy as np
from PIL import Image
from layered_cartoon_head import ROOT
from painted_character import rotation


class CartoonUpperFace:
    def __init__(self, root=ROOT, *, folder_name='eye-underlay-v3'):
        folder = root / folder_name
        self.underlay = np.array(Image.open(folder / 'underlay.png').convert('RGBA'))
        self.glasses = np.array(Image.open(folder / 'glasses.png').convert('RGBA'))
        expression = root / 'expression-rig'
        clean = np.array(Image.open(expression / 'browless-head.png').convert('RGBA'))
        self.forehead = np.array(Image.open(expression / 'forehead-mask.png')).astype('float32') / 255
        repair = np.array(Image.open(expression / 'repair-mask.png')) > 0
        self.pivots = json.loads((expression / 'manifest.json').read_text())['pivots']
        self.brows = {name: np.array(Image.open(expression / f'brow-{name}.png').convert('RGBA')).astype('float32') for name in ('left', 'right')}
        self.domain = np.any(self.underlay != clean, axis=2) | (self.glasses[:, :, 3] > 0) | repair | (self.forehead > 0)
        if self.domain[310:].any():
            raise ValueError('Upper-face ownership crossed speech boundary')
        from cartoon_eyelids import CartoonEyelids
        self.eyelids = CartoonEyelids(self.underlay, root)
        self.yy, self.xx = np.mgrid[:512, :512]
        weight = np.clip((353 - self.xx) / 27, 0, 1)
        self.weight = weight * weight * (3 - 2 * weight)

    def glasses_plane(self, amount):
        if not np.isfinite(amount) or not 0 <= amount <= 25:
            raise ValueError('Glasses lowering must be finite and within 0..25 pixels')
        if amount == 0:
            return self.glasses.copy()
        scale = 1 - .35 * amount / 25 * self.weight
        my = ((self.yy - 245 - amount * self.weight) / scale + 245).astype('float32')
        art = self.glasses.astype('float32')
        art[:, :, :3] *= art[:, :, 3:4] / 255
        art = cv2.remap(art, self.xx.astype('float32'), my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        art[:, :, :3] *= 255 / np.maximum(art[:, :, 3:4], 1)
        result = np.clip(art, 0, 255).astype('uint8')
        result[:, 353:] = self.glasses[:, 353:]
        return result

    def render(self, speech, expression, amount, *, blink=0.):
        base = np.array(speech)
        if base.shape != (512, 512, 4) or base.dtype != np.uint8:
            raise ValueError('Expected native 512x512 RGBA speech face')
        values = {name + key: float(expression.get(name + key, 0)) for name in self.brows for key in ('Tilt', 'Raise')}
        if not np.isfinite(list(values.values())).all():
            raise ValueError('Expected finite brow controls')
        image = base.copy()
        foundation = self.eyelids.pose(blink)
        domain = self.domain | (self.eyelids.domain if blink else False)
        image[domain] = foundation[domain]
        canvas = image.astype('float32')
        canvas[:, :, :3] *= canvas[:, :, 3:4] / 255
        for name, raw in self.brows.items():
            matrix = rotation(self.pivots[name], float(np.clip(values[name + 'Tilt'], -8, 8)))
            matrix[1, 2] -= float(np.clip(values[name + 'Raise'], -8, 8))
            art = raw.copy()
            art[:, :, :3] *= art[:, :, 3:4] / 255
            art = cv2.warpAffine(art, matrix[:2], (512, 512), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
            art *= self.forehead[:, :, None]
            canvas = art + canvas * (1 - art[:, :, 3:4] / 255)
        canvas[:, :, :3] *= 255 / np.maximum(canvas[:, :, 3:4], 1)
        result = Image.fromarray(np.clip(canvas, 0, 255).astype('uint8'))
        glasses = self.glasses_plane(amount)
        domain = domain | (glasses[:, :, 3] > 0)
        if domain[310:].any():
            raise ValueError('Moved glasses crossed speech boundary')
        result.alpha_composite(Image.fromarray(glasses))
        result = np.array(result)
        # Keep untouched speech pixels byte-exact through associated-alpha composition.
        result[~domain] = base[~domain]
        return Image.fromarray(result)


def skeptical_glasses(t, plan):
    from skeptical_cartoon_review import skeptical_event
    from painted_timing import flowing_track
    if not np.isfinite(t):
        raise ValueError('Expected finite review time')
    event = skeptical_event(plan)
    if event is None:
        return 0.
    return float(np.clip(flowing_track(t, [(event['anticipate'], 0.), (event['arrive'], 25.), (event['hold'], 25.), (event['settle'], 0.)]), 0, 25))


def skeptical_blink(t, plan):
    """One authored blink on 'browser' while the glasses are held down."""
    from skeptical_cartoon_review import skeptical_event
    from painted_timing import flowing_track
    if not np.isfinite(t):
        raise ValueError('Expected finite review time')
    event = skeptical_event(plan)
    if event is None:
        return 0.
    word = next(w for w in plan['words'] if w['scriptIndex'] == event['scriptIndices'][4])
    a, b = word['start'], word['end']
    if not np.isfinite([a, b]).all() or b <= a:
        raise ValueError('Expected a finite positive browser interval')
    mid = (a+b)/2
    lead = min(.10, (mid-event['arrive'])*.8)
    tail = min(.20, (event['hold']-mid)*.8)
    if min(lead, tail) <= 0:
        raise ValueError('Blink must fit inside the lowered-glasses hold')
    # shortcut: one authored accent, not automatic emotion or eye-gaze inference.
    keys = [(mid-lead, 0.), (mid-lead*.15, 1.), (mid+tail*.175, 1.), (mid+tail, 0.)]
    return float(np.clip(flowing_track(t, keys), 0, 1))
