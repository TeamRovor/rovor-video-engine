"""Opt-in registered cartoon forearm; cuff-constrained skin and independent wrist.

No default scene import, independent fingers or polished-animation acceptance.
"""
import hashlib, json
import numpy as np
from PIL import Image, ImageDraw
from cartoon_body import CartoonArm, ROOT
from elbow_arc_review import ElbowArcReview
from painted_character import rotation, smooth

class CuffRegisteredForearm(CartoonArm):

    def __init__(self, rig):
        self.rig = rig
        self.geometry = rig.geometry
        r = json.loads((ROOT / 'thumb-forearm-v2/Cuff-Registration.json').read_text())
        self.registration = r
        self.guides = np.asarray(r["sourceGuides"], float)
        source = ROOT / 'thumb-forearm-v2/source.png'
        if hashlib.sha256(source.read_bytes()).hexdigest() != r['sourceSha256']:
            raise ValueError('Forearm source/registration mismatch')
        if any((not np.array_equal(rig.geometry[k], v) for (k, v) in r['targetGeometry'].items())):
            raise ValueError('Expected registered right-arm geometry')
        self.clothing = ElbowArcReview(self.rig)
        mask = Image.new('L', (1024, 1536), 255)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in self.registration['clothingExclusionPolygon']], fill=0)
        self.clothing.image = self.clothing.image * (np.array(mask) > 0)[:, :, None]
        raw = np.array(Image.open(ROOT / 'thumb-forearm-v2/source.png').convert('RGBA'))
        self.image = raw.astype('float32')
        self.image[:, :, :3] *= self.image[:, :, 3:4] / 255
        self.image = np.rint(self.image).astype('uint8')
        (h, w) = raw.shape[:2]
        xs = np.unique(np.r_[np.arange(0, w, 24), w - 1])
        end = r['componentDomainYMax']
        ys = np.unique(np.r_[np.arange(0, end, 24), 850.0, 1300.0, end])
        self.vertices = np.array([(x, y) for y in ys for x in xs], np.float32)
        self.triangles = []
        nx = len(xs)
        for j in range(len(ys) - 1):
            for i in range(nx - 1):
                k = j * nx + i
                for ids in [(k, k + 1, k + nx + 1), (k, k + nx + 1, k + nx)]:
                    tri = self.vertices[list(ids)]
                    lo = np.floor(tri.min(0) - 3).astype(int)
                    hi = np.ceil(tri.max(0) + 3).astype(int)
                    a = raw[max(0, lo[1]):min(h, hi[1] + 1), max(0, lo[0]):min(w, hi[0] + 1), 3]
                    if a.size and a.max() > 0:
                        self.triangles.append(ids)
        (x, y) = self.vertices.T
        center = np.interp(y, self.guides[:, 0], self.guides[:, 1])
        width = np.interp(y, self.guides[:, 0], self.guides[:, 2])
        targetwidth = np.interp(y, [850, 1300, 1400], [52, 68, 72])
        targetcenter = np.interp(y, [850, 1300, 1400], [-5.5, -7, -7.5])
        q = (x - center) * targetwidth / width + targetcenter
        s = np.where(y <= 850, (850 - y) * 52 / 236, (850 - y) * 175 / 550)
        axis = np.array([61.0, 137.0])
        axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        self.material = np.array([810.0, 762.0]) + s[:, None] * axis + q[:, None] * normal

    def _base_vertices(self, a):
        fore = self.rig.hand_parent([a[0], a[1], 0])
        wrist = np.array([810.0, 762.0])
        axis = np.array([61.0, 137.0])
        axis /= np.linalg.norm(axis)
        w = smooth(((self.material - wrist) @ axis + 30) / 60)
        p = self.material.copy()
        delta = (np.c_[p, np.ones(len(p))] @ rotation(wrist, a[2]).T)[:, :2] - p
        p += delta * w[:, None]
        return (np.c_[p, np.ones(len(p))] @ fore.T)[:, :2]

    def posed_vertices(self, a):
        self.rig.hand_parent(a)
        base = self._base_vertices(a)
        (x, y) = self.vertices.T
        guide = self.rig.posed_points(self.registration['cuffOpeningGuide'], a)
        c1 = guide.mean(0)
        d1 = guide[1] - guide[0]
        out1 = np.array([d1[1], -d1[0]])
        out1 /= np.linalg.norm(out1)
        axis = np.array([61.0, 137.0])
        axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        sg = self.rig.posed_points(np.array([810.0, 762.0]) + np.array([-31.5, 20.5])[:, None] * normal, a)
        c0 = sg.mean(0)
        d0 = sg[1] - sg[0]
        out0 = np.array([d0[1], -d0[0]])
        out0 /= np.linalg.norm(out0)
        c1 = c1 - self.registration['underlapDepth'] * out1
        t = np.clip((y - 850) / 450, 0, 1)
        length = np.linalg.norm(c1 - c0)
        m0 = -out0 * length
        m1 = -out1 * length
        center = (2 * t ** 3 - 3 * t ** 2 + 1)[:, None] * c0 + (t ** 3 - 2 * t ** 2 + t)[:, None] * m0 + (-2 * t ** 3 + 3 * t ** 2)[:, None] * c1 + (t ** 3 - t ** 2)[:, None] * m1
        tangent = (6 * t * t - 6 * t)[:, None] * c0 + (3 * t * t - 4 * t + 1)[:, None] * m0 + (-6 * t * t + 6 * t)[:, None] * c1 + (3 * t * t - 2 * t)[:, None] * m1
        n = np.c_[tangent[:, 1], -tangent[:, 0]]
        n /= np.linalg.norm(n, axis=1)[:, None]
        center -= np.maximum(y - 1300, 0)[:, None] * 0.22 * out1
        # The proximal frame must stay fixed when the wrist changes.
        proximal = t == 1
        n[proximal] = d1 / np.linalg.norm(d1)
        center[proximal] = c1 - np.maximum(y[proximal] - 1300, 0)[:, None] * 0.22 * out1
        sourcecenter = np.interp(y, self.guides[:, 0], self.guides[:, 1])
        sourcewidth = np.interp(y, self.guides[:, 0], self.guides[:, 2])
        width = np.linalg.norm(d0) + (np.linalg.norm(d1) - np.linalg.norm(d0)) * smooth(t)
        width = np.where(t == 1, np.linalg.norm(d1), width)
        q = (x - sourcecenter) / sourcewidth * width
        target = center + q[:, None] * n
        return np.where((y >= 850)[:, None], target, base)

    def layer(self, a):
        canvas = Image.new('RGBA', (1464, 1536))
        for arm in [self, self.clothing]:
            (im, xy) = arm.render(a)
            canvas.alpha_composite(im, (xy[0] + 220, xy[1]))
        return canvas
