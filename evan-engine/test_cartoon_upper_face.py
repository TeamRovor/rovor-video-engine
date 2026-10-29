import unittest
import numpy as np
from PIL import Image
from cartoon_upper_face import CartoonUpperFace


class UpperFaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = CartoonUpperFace()

    def test_speech_pixels_and_unowned_alpha_survive(self):
        base = np.random.default_rng(4).integers(0, 256, (512, 512, 4), dtype=np.uint8)
        for amount in (0, 12, 18, 25):
            result = np.array(self.rig.render(Image.fromarray(base), {'leftRaise': 7, 'rightTilt': -4}, amount))
            domain = self.rig.domain | (self.rig.glasses_plane(amount)[:, :, 3] > 0)
            np.testing.assert_array_equal(result[310:], base[310:])
            np.testing.assert_array_equal(result[~domain], base[~domain])

    def test_glasses_ear_anchor_and_speech_guard_all_amounts(self):
        np.testing.assert_array_equal(self.rig.glasses_plane(0), self.rig.glasses)
        for amount in np.linspace(0, 25, 241):
            plane = self.rig.glasses_plane(amount)
            np.testing.assert_array_equal(plane[:, 353:], self.rig.glasses[:, 353:])
            self.assertFalse(plane[310:, :, 3].any())

    def test_brows_move_independently(self):
        base = Image.fromarray(self.rig.underlay)
        neutral = np.array(self.rig.render(base, {}, 25))
        left = np.array(self.rig.render(base, {'leftRaise': 8}, 25))
        right = np.array(self.rig.render(base, {'rightRaise': 8}, 25))
        self.assertGreater(np.any(left != neutral, axis=2).sum(), 100)
        self.assertGreater(np.any(right != neutral, axis=2).sum(), 100)
        np.testing.assert_array_equal(left[:, 235:], neutral[:, 235:])
        np.testing.assert_array_equal(right[:, :235], neutral[:, :235])

    def test_invalid_inputs(self):
        base = Image.fromarray(self.rig.underlay)
        for amount in (-1, 25.01, np.nan, np.inf):
            with self.assertRaises(ValueError):
                self.rig.render(base, {}, amount)
        with self.assertRaises(ValueError):
            self.rig.render(base, {'leftRaise': np.nan}, 0)
        with self.assertRaises(ValueError):
            self.rig.render(Image.new('RGB', (512, 512)), {}, 0)

    def test_word_anchored_cue_and_missing_phrase(self):
        from cartoon_upper_face import skeptical_glasses
        from skeptical_cartoon_review import skeptical_event
        words = "that's not some random browser thing".split()
        plan = {'words': [dict(word=w, start=5+i*.3, end=5.2+i*.3, scriptIndex=i) for i, w in enumerate(words)]}
        event = skeptical_event(plan)
        self.assertEqual(skeptical_glasses(event['anticipate']-.1, plan), 0)
        self.assertEqual(skeptical_glasses(event['arrive'], plan), 25)
        self.assertEqual(skeptical_glasses(event['settle']+.1, plan), 0)
        shifted = {'words': [dict(w, start=w['start']+2, end=w['end']+2) for w in plan['words']]}
        for t in np.linspace(4, 8, 101):
            self.assertAlmostEqual(skeptical_glasses(t, plan), skeptical_glasses(t+2, shifted))
            self.assertTrue(0 <= skeptical_glasses(t, plan) <= 25)
        self.assertEqual(skeptical_glasses(5, {'words': []}), 0)
        with self.assertRaises(ValueError):
            skeptical_glasses(np.nan, plan)


if __name__ == '__main__':
    unittest.main()
