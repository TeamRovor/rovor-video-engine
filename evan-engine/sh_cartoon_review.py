"""Opt-in SH shape identity on existing oral planes; no timing or jaw edits."""
import numpy as np
from painted_timing import flowing_track


def sh_shape_weights(t, plan, baseline):
    shape = np.asarray(baseline, float).copy()
    if not np.isfinite(t) or shape.shape != (9,) or not np.isfinite(shape).all() or (shape < 0).any() or not np.isclose(shape.sum(), 1):
        raise ValueError('Expected finite time and normalized nine-component shape identity')
    if shape[0] >= 1-1e-9:
        return shape
    amount = .35*sh_amount(t, plan)
    if amount == 0:
        return shape
    free = [0, 2, 3, 4, 5, 6, 8]
    budget = float(shape[free].sum())
    shape[free] *= 1-amount
    shape[5] += budget*amount
    return shape


def sh_amount(t, plan):
    if not np.isfinite(t):
        raise ValueError('Expected finite time')
    amount = 0.
    for phone in plan.get('phonemes', []):
        if phone['phone'].rstrip('012') != 'SH':
            continue
        a, b = phone['start'], phone['end']
        if not np.isfinite([a, b]).all() or b <= a:
            raise ValueError('Expected ordered SH interval')
        ramp = min(.03, (b-a)/3)
        amount = max(amount, flowing_track(t, [(a, 0.), (a+ramp, 1.), (b-ramp, 1.), (b, 0.)]))
    return amount


def sh_corner_target(t, plan, oral, contact):
    """Narrow only the existing oral X coordinates; keep every Y anchor."""
    result = np.asarray(oral).copy()
    if result.ndim != 2 or result.shape[0] < 32 or result.shape[1] != 2 or not np.isfinite(result).all() or not np.isfinite(contact) or not 0 <= contact <= 1:
        raise ValueError('Expected finite oral mesh and contact strength0..1')
    amount = .25*sh_amount(t, plan)*(1-contact)**2
    if amount == 0:
        return result
    center = (result[0,0]+result[8,0])/2
    result[:32,0] = center+(result[:32,0]-center)*(1-amount)
    return result
