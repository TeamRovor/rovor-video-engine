import unittest
from render_profile import frame_count, ScaledDraw


class RenderProfileTests(unittest.TestCase):
    def test_original_take_keeps_last_partial_frame(self):
        self.assertEqual(frame_count(22.047375), 1323)
        self.assertGreaterEqual(frame_count(22.047375) / 60, 22.047375)

    def test_legacy_study_duration_preserved(self):
        self.assertEqual(frame_count(231 / 48), 289)
        self.assertLess(frame_count(231 / 48) / 60 - 231 / 48, 1 / 60)

    def test_invalid_clock(self):
        for duration, fps in [(0, 60), (float('nan'), 60), (1, 0), (1, True)]:
            with self.assertRaises(ValueError):
                frame_count(duration, fps)

    def test_graphics_render_at_output_coordinates(self):
        from PIL import Image
        image = Image.new('RGB', (1920, 1080), 'white')
        ScaledDraw(image, 1.5).rectangle((100, 100, 200, 200), fill='black')
        self.assertEqual(image.getpixel((150, 150)), (0, 0, 0))
        self.assertEqual(image.getpixel((100, 100)), (255, 255, 255))


if __name__ == '__main__':
    unittest.main()
