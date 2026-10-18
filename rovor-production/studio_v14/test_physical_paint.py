"""Failures which V13's 7 structural smoke tests did not cover.
These tests CERTIFY contact geometry, never artistic approval.
"""
import io
import math
import unittest
from dataclasses import replace
from PIL import Image
import cairosvg
from physical_paint import Pose,ContactPaint,two_bone_ik
from painter_contact_v14 import PAINT_FIELD,contact_pose,wall_paint,svg_frame,render_png,DURATION


class TestPhysicalContact(unittest.TestCase):
    def test_real_length_inverse_kinematics(self):
        for f in range(421):
            p=contact_pose(f/60)
            self.assertAlmostEqual(math.dist(p.shoulder,p.elbow),147,places=4)
            self.assertAlmostEqual(math.dist(p.elbow,p.wrist),155,places=4)
            self.assertLess(math.dist(p.wrist,p.handle),24)

    def test_unreachable_pose_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unreachable'):
            two_bone_ik((0,0),(400,0),147,155)

    def test_paint_only_during_contact(self):
        self.assertEqual(PAINT_FIELD.strokes_at(83), ())  # frame just before t=.7
        self.assertFalse(PAINT_FIELD.point_covered(525,470,.69))
        self.assertTrue(PAINT_FIELD.point_covered(525,470,.74))
        self.assertFalse(PAINT_FIELD.point_covered(627,400,4.5))
        self.assertTrue(PAINT_FIELD.point_covered(627,400,5.9))

    def test_no_paint_ahead_of_roller(self):
        for t in [.8,1.4,2.,2.5]:
            p=contact_pose(t)
            self.assertFalse(PAINT_FIELD.point_covered(p.roller_x,p.roller_y-25,t))
            self.assertTrue(PAINT_FIELD.point_covered(p.roller_x,475,t))
        for t in [4.82,5.25,5.7]:
            p=contact_pose(t)
            self.assertFalse(PAINT_FIELD.point_covered(p.roller_x,p.roller_y-25,t))
            self.assertTrue(PAINT_FIELD.point_covered(p.roller_x,435,t))

    def test_paint_persists_after_tool_leaves(self):
        points=[(525,465),(525,400),(525,350),(627,410),(627,350)]
        for x,y in points:
            self.assertTrue(PAINT_FIELD.point_covered(x,y,6.8),(x,y))
            self.assertTrue(PAINT_FIELD.point_covered(x,y,7.0),(x,y))

    def test_stroke_location_must_match_centerline(self):
        for t in [.71,1.,2.,3.2,4.9,5.5,6.8]:
            p=contact_pose(t)
            if p.contact:
                self.assertTrue(PAINT_FIELD.point_covered(p.roller_x,p.roller_y,t))
            self.assertFalse(PAINT_FIELD.point_covered(750,300,t))
        # An old hardcoded second rectangle would erroneously paint earlier.
        self.assertFalse(PAINT_FIELD.point_covered(627,350,4.79))

    def test_unmatched_tool_depth_fails_closed(self):
        def liar(t):
            p=contact_pose(t)
            return replace(p,normal_gap=25.0) if p.contact else p
        with self.assertRaisesRegex(ValueError,'off wall'):
            ContactPaint(liar,duration=7,fps=60)

    def test_stretched_arm_fails_closed(self):
        def liar(t):
            p=contact_pose(t)
            return replace(p,elbow=(0,0))
        with self.assertRaisesRegex(ValueError,'stretched'):
            ContactPaint(liar,duration=7,fps=60)

    def test_contact_outside_wall_fails_closed(self):
        def liar(t):
            p=contact_pose(t)
            return replace(p,roller_x=8.0) if p.contact else p
        with self.assertRaisesRegex(ValueError,'outside wall'):
            ContactPaint(liar,duration=7,fps=60)

    def test_lateral_shift_during_contact_needs_model(self):
        def liar(t):
            p=contact_pose(t)
            return replace(p,roller_x=p.roller_x+0.5*t)
        with self.assertRaisesRegex(ValueError,'x changed'):
            field=ContactPaint(liar,duration=7,fps=60)
            field.svg_mask(3)

    def test_independent_svg_portrait_and_landscape(self):
        for orientation in ['landscape','portrait']:
            svg=svg_frame(2.1,orientation)
            self.assertIn('data-pass="0"',svg)
            self.assertIn('id="roller_tool"',svg)
            self.assertIn('id="painter"',svg)
        self.assertNotEqual(svg_frame(2.1,'portrait'),svg_frame(2.1,'landscape'))

    def test_actual_rgba_wall_pigment_at_real_contact(self):
        # Inspect RENDERED scene pixels; not merely string matches or motion specs.
        def rgb(t, xy):
            im=Image.open(io.BytesIO(render_png(t,None,output_width=640,output_height=360))).convert('RGB')
            return im.getpixel((xy[0]//2,xy[1]//2))
        before=rgb(.35,(525,420));after=rgb(2.6,(525,420))
        self.assertGreater(before[0]-after[0],35)
        early=rgb(2.6,(627,400));late=rgb(6.8,(627,400))
        self.assertGreater(early[0]-late[0],35)

    def test_source_does_not_contain_handpainted_rectangles(self):
        import inspect
        from painter_contact_v14 import wall_paint
        source=inspect.getsource(wall_paint)
        self.assertIn('PAINT_FIELD.svg_mask',source)
        self.assertNotIn('M 576 441',source)


if __name__=='__main__':
    unittest.main()