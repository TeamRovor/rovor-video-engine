"""Opt-in finite-radius elbow study; not imported by the speaking scene."""
from copy import deepcopy
import numpy as np
from cartoon_body import CartoonArm
from painted_character import rotation, smooth


class ElbowArcReview(CartoonArm):
    def __init__(self, arm):
        self.image = arm.image.copy()
        self.geometry = deepcopy(arm.geometry)
        self.vertices = arm.vertices.copy()
        self.triangles = arm.triangles.copy()

    @staticmethod
    def _angles(angles):
        a = np.asarray(angles, float)
        if (a.shape != (3,) or not np.isfinite(a).all()
                or not -5 <= a[0] <= 0 or not -135 <= a[1] <= 0 or not -15 <= a[2] <= 15):
            raise ValueError('Review envelope: shoulder -5..0, elbow -135..0, wrist -15..15')
        return a

    def _bend(self, points, degrees):
        p = np.asarray(points, float)
        elbow = np.asarray(self.geometry['elbow'], float)
        axis = np.asarray(self.geometry['wrist'], float) - elbow
        axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        if degrees != 0:
            # Spread curvature over 220 source pixels so the cuff's inside edge does not reverse.
            s = (p - elbow) @ axis
            q = (p - elbow) @ normal
            u = np.clip(s + 110, 0, 220)
            k = np.deg2rad(degrees) / 220
            theta = k * u
            center = (elbow - 110 * axis + np.sin(theta)[:, None] / k * axis
                      + (1 - np.cos(theta))[:, None] / k * normal)
            tangent = np.cos(theta)[:, None] * axis + np.sin(theta)[:, None] * normal
            n = -np.sin(theta)[:, None] * axis + np.cos(theta)[:, None] * normal
            p = center + tangent * (s + 110 - u)[:, None] + n * q[:, None]
        return p

    def hand_parent(self, angles):
        """Proper rigid source-to-posed transform beyond the wrist blend."""
        a = self._angles(angles)
        wrist = np.asarray(self.geometry['wrist'], float)
        forearm = rotation([0, 0], a[1]).astype(float)
        forearm[:2, 2] = self._bend([wrist], a[1])[0] - forearm[:2, :2] @ wrist
        return rotation(self.geometry['shoulder'], a[0]) @ forearm @ rotation(wrist, a[2])

    def posed_vertices(self, angles):
        return self.posed_points(self.vertices, angles)

    def posed_points(self, points, angles):
        """Pose registered component guides in the same material coordinates as the arm."""
        a = self._angles(angles)
        points = np.asarray(points, float)
        if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
            raise ValueError('Expected finite N-by-2 material points')
        p = self._bend(points, a[1])
        if a[2] != 0:
            wrist = np.asarray(self.geometry['wrist'], float)
            axis = wrist - self.geometry['elbow']
            axis /= np.linalg.norm(axis)
            w = smooth(((points - wrist) @ axis + 30) / 60)
            delta = (np.c_[points, np.ones(len(p))] @ rotation(wrist, a[2]).T)[:, :2] - points
            # Wrist influence begins beyond the elbow arc, so its displacement uses the rigid forearm parent.
            p = p + (delta * w[:, None]) @ rotation([0, 0], a[1])[:2, :2].T
        return (np.c_[p, np.ones(len(p))] @ rotation(self.geometry['shoulder'], a[0]).T)[:, :2]
