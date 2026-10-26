"""Opt-in finite-radius elbow study; not imported by the speaking scene."""
from copy import deepcopy
import numpy as np
from cartoon_body import CartoonArm
from painted_character import rotation


class ElbowArcReview(CartoonArm):
    def __init__(self, arm):
        self.image = arm.image.copy()
        self.geometry = deepcopy(arm.geometry)
        self.vertices = arm.vertices.copy()
        self.triangles = arm.triangles.copy()

    def posed_vertices(self, angles):
        a = np.asarray(angles, float)
        # shortcut: wrist stays rigid with the forearm; fit its moved parent before adding wrist or hand-pose controls.
        if (a.shape != (3,) or not np.isfinite(a).all()
                or not -5 <= a[0] <= 0 or not -135 <= a[1] <= 0 or a[2] != 0):
            raise ValueError('Review envelope: shoulder -5..0, elbow -135..0, wrist zero')
        p = self.vertices.astype(float)
        elbow = np.asarray(self.geometry['elbow'], float)
        axis = np.asarray(self.geometry['wrist'], float) - elbow
        axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        if a[1] != 0:
            # Spread curvature over 220 source pixels so the cuff's inside edge does not reverse.
            s = (p - elbow) @ axis
            q = (p - elbow) @ normal
            u = np.clip(s + 110, 0, 220)
            k = np.deg2rad(a[1]) / 220
            theta = k * u
            center = (elbow - 110 * axis + np.sin(theta)[:, None] / k * axis
                      + (1 - np.cos(theta))[:, None] / k * normal)
            tangent = np.cos(theta)[:, None] * axis + np.sin(theta)[:, None] * normal
            n = -np.sin(theta)[:, None] * axis + np.cos(theta)[:, None] * normal
            p = center + tangent * (s + 110 - u)[:, None] + n * q[:, None]
        return (np.c_[p, np.ones(len(p))] @ rotation(self.geometry['shoulder'], a[0]).T)[:, :2]
