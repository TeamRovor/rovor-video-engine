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

    def test_word_anchored_blink_shift_bounds_and_missing_phrase(self):
        from cartoon_upper_face import skeptical_blink, skeptical_glasses
        words = "that's not some random browser thing".split()
        plan = {'words': [dict(word=w, start=5+i*.3, end=5.2+i*.3, scriptIndex=i) for i, w in enumerate(words)]}
        shifted = {'words': [dict(w, start=w['start']+2, end=w['end']+2) for w in plan['words']]}
        for t in np.linspace(4, 8, 401):
            value = skeptical_blink(t, plan)
            self.assertTrue(0 <= value <= 1)
            self.assertAlmostEqual(value, skeptical_blink(t+2, shifted))
            if value:
                self.assertAlmostEqual(skeptical_glasses(t, plan), 25)
        mid = (plan['words'][4]['start']+plan['words'][4]['end'])/2
        self.assertEqual(skeptical_blink(mid, plan), 1)
        self.assertEqual(skeptical_blink(mid-.11, plan), 0)
        self.assertEqual(skeptical_blink(mid+.21, plan), 0)
        self.assertEqual(skeptical_blink(5, {'words': []}), 0)
        with self.assertRaises(ValueError):
            skeptical_blink(np.nan, plan)
        invalid = {'words': [dict(w) for w in plan['words']]}
        invalid['words'][4]['end'] = invalid['words'][4]['start']
        with self.assertRaises(ValueError):
            skeptical_blink(mid, invalid)

    def test_left_upper_is_independent_and_full_blink_wins(self):
        source = self.lids.source.copy()
        for blink in (0, .5, 1):
            baseline = self.lids.pose(blink)
            candidate = self.lids.pose(blink, left_upper=.55)
            np.testing.assert_array_equal(candidate[:, 215:], baseline[:, 215:])
            np.testing.assert_array_equal(candidate[~self.lids.domain], baseline[~self.lids.domain])
            if blink == 1:
                np.testing.assert_array_equal(candidate, baseline)
            else:
                self.assertGreater(np.any(candidate != baseline, axis=2).sum(), 20)
            before = self.lids.planes(blink or .01)
            after = self.lids.planes(blink or .01, left_upper=.55)
            np.testing.assert_array_equal(before[1], after[1])  # Lower plane stays put.
            for a, b in zip(before[3:], after[3:]):
                np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(self.lids.source, source)
        base = Image.fromarray(self.rig.underlay)
        before = np.array(self.rig.render(base, {}, 25))
        after = np.array(self.rig.render(base, {}, 25, left_upper=.55))
        np.testing.assert_array_equal(after[310:], before[310:])
        opaque = self.rig.glasses_plane(25)[:, :, 3] == 255
        np.testing.assert_array_equal(after[opaque], before[opaque])
        for amount in (-.01, 1.01, np.nan, np.inf):
            with self.assertRaises(ValueError):
                self.lids.pose(0, left_upper=amount)

    def test_skeptical_narrowing_shift_bounds_and_rest(self):
        from cartoon_upper_face import skeptical_narrowing
        from skeptical_cartoon_review import skeptical_event
        words = "that's not some random browser thing".split()
        plan = {'words': [dict(word=w, start=5+i*.3, end=5.2+i*.3, scriptIndex=i) for i, w in enumerate(words)]}
        shifted = {'words': [dict(w, start=w['start']+2, end=w['end']+2) for w in plan['words']]}
        event = skeptical_event(plan)
        values=[]
        for t in np.arange(4, 8, 1/480):
            v=skeptical_narrowing(t,plan);values.append(v)
            self.assertTrue(0 <= v <= .35)
            self.assertAlmostEqual(v,skeptical_narrowing(t+2,shifted))
            if t <= event['arrive'] or t >= event['settle']:
                self.assertEqual(v,0)
        self.assertLess(float(abs(np.diff(values)).max()),.006)
        self.assertEqual(skeptical_narrowing(event['hold'],plan),.35)
        self.assertEqual(skeptical_narrowing(6,{'words':[]}),0)
        with self.assertRaises(ValueError):
            skeptical_narrowing(np.nan,plan)


if __name__ == '__main__':
    unittest.main()
