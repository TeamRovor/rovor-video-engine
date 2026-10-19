"""Optional drawn-contour correspondence for the rounded oral art candidate.

The alpha silhouette supplies a polar boundary, not phonetic/anatomical truth.
Both existing oral drawings move to one interpolated contour before mixing.
No new source pixels, face patches, audio timing or geometry controls.
"""
import cv2
import numpy as np
from bounded_cartoon_head import BoundedCartoonHead
from rounded_art_cartoon_head import RoundedArtCartoonHead, rounded_art_strength
from layered_cartoon_head import over, ROOT
from cartoon_head import POINTS

ANGLES = np.arange(256, dtype=np.float32) * (2*np.pi/256)

def silhouette_profile(surface):
    """Ray intersections with largest 50%-alpha contour, starting at +x.

    Use the outermost ray intersection where the old ink has small notches.
    Concave internal ink is retained, not traced as a second outer boundary.
    This is radial envelope correspondence, not anatomical retopology.
    """
    alpha = cv2.resize(surface[:, :, 3], None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR)
    mask = (alpha >= 127.5).astype('uint8')
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError('No opaque oral contour')
    contour = max(contours, key=cv2.contourArea)[:, 0].astype(np.float32)/4 - .375
    moments = cv2.moments(contour)
    if moments['m00'] <= 4:
        raise ValueError('Oral contour too small')
    center = np.array([moments['m10']/moments['m00'], moments['m01']/moments['m00']], np.float32)
    a = contour-center
    v = np.roll(contour, -1, axis=0)-contour
    direction = np.stack([np.cos(ANGLES), np.sin(ANGLES)], axis=1)
    # cross(a,v)/cross(d,v) and cross(a,d)/cross(d,v).
    denominator = direction[:, 0, None]*v[None, :, 1]-direction[:, 1, None]*v[None, :, 0]
    valid = np.abs(denominator) > 1e-6
    distance = np.zeros_like(denominator)
    segment = np.zeros_like(denominator)
    np.divide(a[:, 0]*v[:, 1]-a[:, 1]*v[:, 0], denominator, out=distance, where=valid)
    np.divide(a[None, :, 0]*direction[:, 1, None]-a[None, :, 1]*direction[:, 0, None], denominator, out=segment, where=valid)
    hits = valid & (distance > 0) & (segment >= 0) & (segment < 1)
    near = np.min(np.where(hits, distance, np.inf), axis=1)
    far = np.max(np.where(hits, distance, 0), axis=1)
    if not np.all(np.isfinite(near)) or np.min(far) <= 0:
        raise ValueError('Oral silhouette has missing rays')
    return center, far

def contour_maps(old, new, strength):
    c0, r0 = silhouette_profile(old)
    c1, r1 = silhouette_profile(new)
    center = c0*(1-strength)+c1*strength
    radii = r0*(1-strength)+r1*strength
    yy, xx = np.mgrid[:old.shape[0], :old.shape[1]].astype(np.float32)
    dx, dy = xx-center[0], yy-center[1]
    angle = np.mod(np.arctan2(dy, dx), 2*np.pi)
    grid = np.r_[ANGLES, 2*np.pi]
    common = np.interp(angle, grid, np.r_[radii, radii[0]])
    fields = []
    for c, r in [(c0, r0), (c1, r1)]:
        ratio = np.interp(angle, grid, np.r_[r, r[0]])/common
        fields.append(((c[0]+dx*ratio).astype('float32'), (c[1]+dy*ratio).astype('float32')))
    return fields

class ContourCartoonHead(RoundedArtCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self._contour_cache = None
        self.contour_fallbacks = 0

    def _aligned_oral(self, w, oral, shape_weights=None):
        strength = rounded_art_strength(w)
        key = oral.tobytes(), float(strength)
        if self._contour_cache is not None and self._contour_cache[0] == key:
            return self._contour_cache[1]
        old = BoundedCartoonHead.cavity_surface(self, w, oral, shape_weights)
        new = over(self.sample_surface(self.round_art['cavity'], POINTS['E'], oral, 2),
                   self.sample_surface(self.round_art['rim'], POINTS['E'], oral, 2))
        try:
            fields = contour_maps(old, new, strength)
        except ValueError:
            # Preserve previous candidate if a contour cannot be registered.
            self.contour_fallbacks += 1
            fields = None
        value = old, new, fields
        self._contour_cache = key, value
        return value

    def _remap(self, surface, field):
        # Linear samples of bounded premultiplied input remain valid and do not
        # reintroduce cubic alpha overshoot around the newly aligned boundary.
        return cv2.remap(surface, *field, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    def cavity_surface(self, w, oral, shape_weights=None):
        s = rounded_art_strength(w)
        if s <= 0 or s >= 1:
            return super().cavity_surface(w, oral, shape_weights)
        old, new, fields = self._aligned_oral(w, oral, shape_weights)
        if fields is not None:
            old, new = self._remap(old, fields[0]), self._remap(new, fields[1])
        return old*(1-s)+new*s

    def interior_mask(self, cavity, w, oral, shape_weights=None):
        s = rounded_art_strength(w)
        if s <= 0 or s >= 1:
            return super().interior_mask(cavity, w, oral, shape_weights)
        old, _, fields = self._aligned_oral(w, oral, shape_weights)
        old_mask = BoundedCartoonHead.interior_mask(self, old, w, oral, shape_weights)
        matte = self.sample_surface(self.round_art['interior-mask'], POINTS['E'], oral, 2)
        new_mask = cv2.erode(matte[:, :, 3], np.ones((3,3), np.uint8))[:, :, None]/255
        if fields is not None:
            old_mask = self._remap(old_mask, fields[0])[:, :, None]
            new_mask = self._remap(new_mask, fields[1])[:, :, None]
        return old_mask*(1-s)+new_mask*s
