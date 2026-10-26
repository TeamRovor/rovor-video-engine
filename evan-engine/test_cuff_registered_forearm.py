import hashlib, unittest, cv2, numpy as np
from cuff_registered_forearm import CuffRegisteredForearm
from finished_cartoon_scene import FinishedCartoonSceneBody
from elbow_arc_review import ElbowArcReview
from cartoon_body import ROOT

class CuffRegistrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1)
        cls.rig = ElbowArcReview(FinishedCartoonSceneBody().arms['right'])
        cls.hand = CuffRegisteredForearm(cls.rig)

    def test_envelope_and_distal_hand(self):
        h = self.hand
        distal = (h.material - self.rig.geometry['wrist']) @ (np.array([61.0, 137.0]) / np.linalg.norm([61, 137])) >= 30
        for s in [-5, -2.5, 0]:
            for e in np.linspace(-135, 0, 136):
                for w in [-15, 0, 15]:
                    a = [s, e, w]
                    p = h.posed_vertices(a)
                    t = p[np.array(h.triangles)]
                    v = t[:, 1:] - t[:, 0, None]
                    self.assertGreater(float((v[:, 0, 0] * v[:, 1, 1] - v[:, 0, 1] * v[:, 1, 0]).min()), 0)
                    expected = (np.c_[h.material[distal], np.ones(distal.sum())] @ self.rig.hand_parent(a).T)[:, :2]
                    np.testing.assert_allclose(p[distal], expected, atol=0.0001)

    def test_raised_cap_is_hidden_and_proximal_skin_held(self):
        h = self.hand
        v = h.vertices
        cap = (v[:, 1] == 1350) & (h.image[v[:, 1].astype(int), v[:, 0].astype(int), 3] >= 128)
        base = h.posed_vertices([-5, -135, 0])
        self.assertGreater(cap.sum(), 0)
        for w in [-15, 0, 15]:
            a = [-5, -135, w]
            p = h.posed_vertices(a)
            np.testing.assert_array_equal(p[v[:, 1] >= 1300], base[v[:, 1] >= 1300])
            (im, xy) = h.clothing.render(a)
            alpha = np.array(im)[:, :, 3]
            points = p[cap] - xy
            values = cv2.remap(alpha, points[:, 0:1].astype('float32'), points[:, 1:2].astype('float32'), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            self.assertGreaterEqual(int(values.min()), 250)

    def test_render_preserves_sources(self):
        source = self.rig.image.copy()
        hand = self.hand.image.copy()
        path = ROOT / 'thumb-forearm-v2/source.png'
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        layer = self.hand.layer([-5, -135, 15])
        self.assertEqual(layer.size, (1464, 1536))
        np.testing.assert_array_equal(self.rig.image, source)
        np.testing.assert_array_equal(self.hand.image, hand)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sha)

    def test_unsupported_inputs_rejected(self):
        for bad in [[0, 0], [0, -136, 0], [0, 0, 16], [0, np.nan, 0]]:
            with self.assertRaises(ValueError):
                self.hand.posed_vertices(bad)
        wrong = ElbowArcReview(self.rig)
        wrong.geometry['wrist'] = [822, 784]
        with self.assertRaises(ValueError):
            CuffRegisteredForearm(wrong)
if __name__ == '__main__':
    unittest.main()
