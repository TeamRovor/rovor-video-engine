import unittest
import cv2
import numpy as np
from PIL import Image
from finished_cartoon_scene import FinishedCartoonSceneBody
from elbow_arc_review import ElbowArcReview
from painted_character import rotation


class ElbowArcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1)
        cls.original = FinishedCartoonSceneBody().arms['right']
        cls.rig = ElbowArcReview(cls.original)

    def test_neutral_geometry_and_source_preservation(self):
        np.testing.assert_array_equal(self.rig.posed_vertices([0, 0, 0]), self.original.vertices)
        source = self.original.image.copy()
        canvases = []
        for arm in [self.original, self.rig]:
            im, (x, y) = arm.render([0, 0, 0])
            canvas = Image.new('RGBA', (1464, 1536))
            canvas.alpha_composite(im, (x + 220, y))
            canvases.append(np.asarray(canvas))
        np.testing.assert_array_equal(*canvases)
        self.rig.render([-5, -135, 15])
        np.testing.assert_array_equal(self.rig.image, self.original.image)
        np.testing.assert_array_equal(self.original.image, source)

    def test_full_envelope_and_rigid_material_outside_bend(self):
        elbow = np.array(self.rig.geometry['elbow'])
        axis = np.array(self.rig.geometry['wrist']) - elbow
        axis = axis / np.linalg.norm(axis)
        s = (self.rig.vertices - elbow) @ axis
        distal = (self.rig.vertices - self.rig.geometry['wrist']) @ axis >= 30
        for shoulder in [0, -2.5, -5]:
            for bend in np.linspace(0, -135, 136):
                for wrist in [-15, 0, 15]:
                    angles = [shoulder, bend, wrist]
                    posed = self.rig.posed_vertices(angles)
                    t = posed[np.array(self.rig.triangles)]
                    v = t[:, 1:] - t[:, 0, None]
                    self.assertGreater(np.min(v[:, 0, 0]*v[:, 1, 1] - v[:, 0, 1]*v[:, 1, 0]), 0)
                    upper = self.rig.vertices[s <= -110]
                    expected = (np.c_[upper, np.ones(len(upper))] @ rotation(self.rig.geometry['shoulder'], shoulder).T)[:, :2]
                    np.testing.assert_allclose(posed[s <= -110], expected, atol=1e-6)
                    parent = self.rig.hand_parent(angles)
                    np.testing.assert_allclose(parent[:2, :2].T @ parent[:2, :2], np.eye(2), atol=1e-6)
                    self.assertGreater(np.linalg.det(parent[:2, :2]), 0)
                    hand = self.rig.vertices[distal]
                    expected = (np.c_[hand, np.ones(len(hand))] @ parent.T)[:, :2]
                    np.testing.assert_allclose(posed[distal], expected, atol=1e-4)

    def test_wrist_keeps_proximal_material_and_moved_anchor(self):
        axis = np.array([61., 137.]); axis /= np.linalg.norm(axis)
        wrist = self.rig.geometry['wrist']
        proximal = (self.rig.vertices - wrist) @ axis <= -30
        for bend in [0, -67.5, -135]:
            base = self.rig.posed_vertices([-5, bend, 0])
            anchor = self.rig.hand_parent([-5, bend, 0]) @ np.r_[wrist, 1]
            for angle in [-15, 15]:
                np.testing.assert_array_equal(self.rig.posed_vertices([-5, bend, angle])[proximal], base[proximal])
                np.testing.assert_allclose(self.rig.hand_parent([-5, bend, angle]) @ np.r_[wrist, 1], anchor, atol=1e-4)

    def test_unsupported_pose_rejected(self):
        for bad in [[0, 0], [0, np.nan, 0], [0, -136, 0], [0, 1, 0], [-6, 0, 0], [1, 0, 0], [0, 0, 16], [0, 0, -16]]:
            for call in [self.rig.posed_vertices, self.rig.hand_parent]:
                with self.assertRaises(ValueError):
                    call(bad)

    def test_registered_component_guides(self):
        axis = np.array([61., 137.]); axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        wrist = np.array(self.rig.geometry['wrist'])
        guides = wrist + np.array([-36, -36, 0, 40, 40])[:, None]*axis + np.array([-24, 24, 0, -40, 40])[:, None]*normal
        base = self.rig.posed_points(guides, [-5, -135, 0])
        for angle in [-15, 0, 15]:
            a = [-5, -135, angle]
            actual = self.rig.posed_points(guides, a)
            np.testing.assert_array_equal(actual[:2], base[:2])
            np.testing.assert_allclose(actual[2], base[2], atol=1e-4)
            expected = (np.c_[guides[3:], np.ones(2)] @ self.rig.hand_parent(a).T)[:, :2]
            np.testing.assert_allclose(actual[3:], expected, atol=1e-4)

    def test_invalid_component_guides(self):
        for bad in [[1, 2], [[1, 2, 3]], [[1, np.nan]], [[np.inf, 0]]]:
            with self.assertRaises(ValueError):
                self.rig.posed_points(bad, [-5, -135, 0])


if __name__ == '__main__':
    unittest.main()
