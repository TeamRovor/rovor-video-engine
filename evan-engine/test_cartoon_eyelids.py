import unittest
import numpy as np
from PIL import Image
from cartoon_upper_face import CartoonUpperFace


class EyelidTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = CartoonUpperFace()
        cls.lids = cls.rig.eyelids

    def test_open_exact_and_no_mutation(self):
        source = self.lids.source.copy()
        np.testing.assert_array_equal(self.lids.pose(0), source)
        self.lids.pose(1)
        np.testing.assert_array_equal(self.lids.source, source)
        np.testing.assert_array_equal(self.lids.pose(0), source)

    def test_closed_covers_stationary_eye_footprints(self):
        planes = self.lids.planes(1)
        closed = self.lids.pose(1)
        for i, eye in enumerate(self.lids.eyes):
            domain = eye[4] > 0
            union = np.maximum(planes[3*i][:, :, 3], planes[3*i+1][:, :, 3])
            self.assertTrue((union[domain] == 255).all())
            rgb = closed[:, :, :3].astype(float)
            white = (np.ptp(rgb, axis=2) < 65) & (rgb.min(axis=2) > 110)
            self.assertFalse(white[domain].any())

    def test_ownership_and_ordered_apertures(self):
        for amount in np.linspace(0, 1, 17):
            result = self.lids.pose(amount)
            np.testing.assert_array_equal(result[~self.lids.domain], self.lids.source[~self.lids.domain])
            np.testing.assert_array_equal(result[310:], self.lids.source[310:])
            np.testing.assert_array_equal(result[:, 215:244], self.lids.source[:, 215:244])
            for _, top, bottom, close, *_ in self.lids.eyes:
                self.assertTrue(np.all(bottom+(close-bottom)*amount >= top+(close-top)*amount - 1e-5))

    def test_speech_and_glasses_unchanged(self):
        base = Image.fromarray(self.rig.underlay)
        rest = np.array(self.rig.render(base, {}, 25))
        closed = np.array(self.rig.render(base, {}, 25, blink=1))
        np.testing.assert_array_equal(rest[310:], closed[310:])
        opaque = self.rig.glasses_plane(25)[:, :, 3] == 255
        np.testing.assert_array_equal(rest[opaque], closed[opaque])
        self.assertGreater(np.any(rest != closed, axis=2).sum(), 100)

    def test_invalid_blink(self):
        for amount in [-.01, 1.01, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                self.lids.pose(amount)


if __name__ == '__main__':
    unittest.main()
