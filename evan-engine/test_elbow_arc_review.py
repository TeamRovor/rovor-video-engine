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
        self.rig.render([-5, -135, 0])
        np.testing.assert_array_equal(self.rig.image, self.original.image)
        np.testing.assert_array_equal(self.original.image, source)

    def test_full_envelope_and_rigid_material_outside_bend(self):
        elbow = np.array(self.rig.geometry['elbow'])
        axis = np.array(self.rig.geometry['wrist']) - elbow
        axis = axis / np.linalg.norm(axis)
        s = (self.rig.vertices - elbow) @ axis
        hand = self.rig.vertices[s >= 110]
        for shoulder in [0, -2.5, -5]:
            for bend in np.linspace(0, -135, 136):
                posed = self.rig.posed_vertices([shoulder, bend, 0])
                t = posed[np.array(self.rig.triangles)]
                v = t[:, 1:] - t[:, 0, None]
                self.assertGreater(np.min(v[:, 0, 0]*v[:, 1, 1] - v[:, 0, 1]*v[:, 1, 0]), 0)
                upper = self.rig.vertices[s <= -110]
                expected = (np.c_[upper, np.ones(len(upper))] @ rotation(self.rig.geometry['shoulder'], shoulder).T)[:, :2]
                np.testing.assert_allclose(posed[s <= -110], expected, atol=1e-6)
                actual = posed[s >= 110]
                np.testing.assert_allclose(np.linalg.norm(actual - actual[0], axis=1),
                                           np.linalg.norm(hand - hand[0], axis=1), atol=1e-4)

    def test_unsupported_pose_rejected(self):
        for bad in [[0, 0], [0, np.nan, 0], [0, -136, 0], [0, 1, 0], [-6, 0, 0], [1, 0, 0], [0, 0, 1]]:
            with self.assertRaises(ValueError):
                self.rig.posed_vertices(bad)


if __name__ == '__main__':
    unittest.main()
