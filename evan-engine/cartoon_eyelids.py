"""Opt-in upper/lower lid planes over a stationary eye drawing."""
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw
from layered_cartoon_head import ROOT


class CartoonEyelids:
    def __init__(self, source, root=ROOT):
        self.source = source.copy()
        folder = root / 'eyelid-skin-v1'
        self.skin = np.array(Image.open(folder / 'skin-underpaint.png').convert('RGBA'))
        self.eyes = []
        self.domain = np.zeros((512, 512), bool)
        yy, xx = np.mgrid[:512, :512]
        for eye in json.loads((folder / 'registration.json').read_text())['eyes']:
            mask = np.zeros((512, 512), np.uint8)
            cv2.fillPoly(mask, [np.array(eye['polygon'], np.int32)], 255)
            x = np.arange(min(p[0] for p in eye['polygon']), max(p[0] for p in eye['polygon']) + 1)
            top = np.array([np.where(mask[:, px])[0].min() for px in x], dtype='float32')
            bottom = np.array([np.where(mask[:, px])[0].max() for px in x], dtype='float32')
            top = cv2.GaussianBlur(top[None, :], (7, 1), 1.5)[0]
            bottom = cv2.GaussianBlur(bottom[None, :], (7, 1), 1.5)[0]
            u = np.linspace(0, 1, len(x))
            close = eye['corners'][0] * (1-u) + eye['corners'][1] * u + eye['depth'] * 4*u*(1-u)
            self.eyes.append((x, top, bottom, close, mask / 255, np.clip(xx-x[0], 0, len(x)-1), yy))
            self.domain |= cv2.dilate(mask, np.ones((9, 9), np.uint8)) > 0
        self.domain[:, 215:244] = False
        if self.domain[310:].any():
            raise ValueError('Eyelid ownership crossed speech boundary')

    def planes(self, amount):
        if not np.isfinite(amount) or not 0 <= amount <= 1:
            raise ValueError('Blink must be finite and within 0..1')
        if amount == 0:
            return []
        result = []
        # shortcut: authored lid curves and 12% ink onset; artist refinement is still required.
        onset = min(1., amount / .12)
        for x, top, bottom, close, mask, col, yy in self.eyes:
            upper = top + (close-top)*amount
            lower = bottom + (close-bottom)*amount
            for coverage in [np.clip(upper[col]-yy+1, 0, 1), np.clip(yy-lower[col]+1, 0, 1)]:
                plane = self.skin.copy()
                plane[:, :, 3] = np.rint(coverage * mask * onset * 255).astype('uint8')
                result.append(plane)
            ink = Image.new('RGBA', (2048, 2048))
            draw = ImageDraw.Draw(ink)
            for curve, width, opacity in [(upper, 6, onset), (lower, 3, onset*(1-amount))]:
                draw.line([(round(px*4), round(py*4)) for px, py in zip(x, curve)], fill=(32, 21, 17, round(255*opacity)), width=width, joint='curve')
            result.append(np.array(ink.resize((512, 512), Image.Resampling.LANCZOS)))
        return result

    def pose(self, amount):
        result = Image.fromarray(self.source)
        for plane in self.planes(amount):
            result.alpha_composite(Image.fromarray(plane))
        posed = np.array(result)
        posed[~self.domain] = self.source[~self.domain]
        return posed
