"""Geometry and routing regressions; passing these is not visual approval."""
import unittest
from animate_evan import frame_command
try:
    import numpy as np
    from painted_character import PaintedCharacter, skin_vertices, arm_transforms
    from painted_face_mesh import POINTS, triangle_areas, blend_drawings
    from painted_timing import speech_weights, flowing_track
    from render_painted_scene import control_state
    from build_painted_rig import ARMS, key_plate
    from PIL import Image
except ImportError:
    np = None


class PaintedBackendTests(unittest.TestCase):
    def test_existing_backend_is_preserved(self):
        cmd = frame_command({'node': 'node'}, 'calibrated', 'scene', 'frames', 3, 50)
        self.assertEqual(cmd[0], 'node')
        self.assertEqual(cmd[1].name, 'render_frames.cjs')
        self.assertEqual(cmd[-2:], [3, 50])

    def test_painted_uses_explicit_python(self):
        cmd = frame_command({'painted_python': 'artist-python'}, 'painted', 'scene', 'frames', 4, 60)
        self.assertEqual(cmd[0], 'artist-python')
        self.assertEqual(cmd[1].name, 'render_painted_scene.py')
        self.assertEqual(cmd[-2:], [4, 60])


@unittest.skipIf(np is None, 'Optional painted rig requires NumPy/Pillow/OpenCV')
class PaintedRigTests(unittest.TestCase):
    def test_chroma_preserves_white_teeth(self):
        plate = Image.new('RGBA', (4, 1))
        plate.putdata([(255, 0, 255, 255), (255, 255, 255, 255), (36, 47, 68, 255), (249, 178, 122, 255)])
        keyed = key_plate(plate)
        self.assertEqual(keyed.getpixel((0, 0))[3], 0)
        for i in (1, 2, 3):
            self.assertEqual(keyed.getpixel((i, 0)), plate.getpixel((i, 0)))

    def test_rest_mesh_is_identity(self):
        points = np.array([[242, 492], [205, 752], [130, 978], [92, 1058], [175, 800]], dtype='float32')
        np.testing.assert_allclose(points, skin_vertices(points, ARMS['left'], (0, 0, 0)), atol=1e-4)

    def test_joint_hierarchy_preserves_bone_lengths(self):
        geo = ARMS['right']
        upper, fore, hand = arm_transforms(geo, (-5, -18, -6))
        elbow = np.r_[geo['elbow'], 1]
        wrist = np.r_[geo['wrist'], 1]
        tip = np.r_[geo['tip'], 1]
        np.testing.assert_allclose(fore @ elbow, upper @ elbow, atol=1e-3)
        np.testing.assert_allclose(hand @ wrist, fore @ wrist, atol=1e-3)
        self.assertAlmostEqual(float(np.linalg.norm((fore @ wrist - fore @ elbow)[:2])), float(np.linalg.norm((wrist - elbow)[:2])), places=3)
        self.assertAlmostEqual(float(np.linalg.norm((hand @ tip - hand @ wrist)[:2])), float(np.linalg.norm((tip - wrist)[:2])), places=3)

    def test_every_face_transition_has_valid_triangles(self):
        sign = np.sign(triangle_areas(POINTS['X']))
        for a in POINTS.values():
            for b in POINTS.values():
                for weight in (0, .25, .5, .75, 1):
                    areas = triangle_areas(a * (1 - weight) + b * weight)
                    self.assertTrue(np.all(np.sign(areas) == sign))
                    self.assertGreater(float(np.min(np.abs(areas))), .01)

    def test_upper_face_is_pixel_stable(self):
        character = PaintedCharacter()
        base = np.asarray(character.face('X', 'X', 1))[:210]
        for a, b, weight in [('A', 'D', .25), ('D', 'F', .5), ('E', 'G', .75), ('H', 'B', .5)]:
            np.testing.assert_array_equal(np.asarray(character.face(a, b, weight))[:210], base)

    def test_fast_mbp_closure_is_preserved(self):
        cues = [{'start': 0, 'end': .2, 'value': 'D'}, {'start': .2, 'end': .23, 'value': 'A'}, {'start': .23, 'end': .4, 'value': 'C'}]
        self.assertAlmostEqual(float(speech_weights(.215, cues)[1]), 1., places=6)
        before = speech_weights(.2 - 1e-5, cues)
        after = speech_weights(.2 + 1e-5, cues)
        self.assertLess(float(np.abs(after - before).sum()), .005)

    def test_speech_weights_have_no_boundary_resets(self):
        cues = [{'start':0,'end':.15,'value':'C'}, {'start':.15,'end':.21,'value':'F'},
                {'start':.21,'end':.25,'value':'G'}, {'start':.25,'end':.4,'value':'D'}]
        for boundary in (.15,.21,.25,.4):
            a=speech_weights(boundary-1e-5,cues);b=speech_weights(boundary+1e-5,cues)
            self.assertLess(float(np.abs(a-b).sum()),.005)
            self.assertAlmostEqual(float(b.sum()),1,places=5)

    def test_authored_motion_flows_through_monotone_keys(self):
        keys=[(0,0),(1,3),(2,4)]
        h=1e-4
        left=(flowing_track(1,keys)-flowing_track(1-h,keys))/h
        right=(flowing_track(1+h,keys)-flowing_track(1,keys))/h
        self.assertAlmostEqual(left,right,places=2)
        self.assertGreater(left,.5)

    def test_conversational_jaw_does_not_slam_to_wide_open(self):
        cues=[{'start':0,'end':1,'value':'D'}]
        weights=speech_weights(.5,cues)
        self.assertLess(float(weights[4]),.71)
        self.assertGreater(float(weights[3]),.25)

    def test_cavity_drawing_changes_without_a_dominant_pose_switch(self):
        character=PaintedCharacter()
        weights=np.zeros(9,np.float32);weights[1]=.2
        weights[3]=.8*37/62;weights[4]=.8*25/62
        a=weights.copy();a[3]-=.0001;a[4]+=.0001
        b=weights.copy();b[3]+=.0001;b[4]-=.0001
        first=blend_drawings(character.heads,a)[200:285,150:245,:3]
        second=blend_drawings(character.heads,b)[200:285,150:245,:3]
        self.assertLess(float(np.abs(first-second).mean()),.3)

    def test_blended_anatomy_does_not_invert_triangles(self):
        rng=np.random.default_rng(47);sign=np.sign(triangle_areas(POINTS['X']))
        for weights in rng.dirichlet(np.ones(9),100):
            target=sum(p*w for p,w in zip(POINTS.values(),weights))
            self.assertTrue(np.all(np.sign(triangle_areas(target))==sign))

    def test_future_gesture_does_not_erase_current_acting(self):
        first={'start':1,'end':2,'kind':'present'}
        future={'start':8,'end':9,'kind':'present'}
        current=control_state(1.3,{'gestures':[first]})
        combined=control_state(1.3,{'gestures':[first,future]})
        np.testing.assert_allclose(combined['left'],current['left'],atol=1e-6)
        self.assertGreater(combined['left'][1],1)
        self.assertIn('body_roll',combined)


if __name__ == '__main__':
    unittest.main()
