"""The old SVG blockout must never accidentally become the default preview."""
from pathlib import Path
import tempfile
import unittest
from cartoon_rig_blockout import render_demo, frame_svg


class ExplicitEngineeringOnlyTests(unittest.TestCase):
    def test_no_render_output_without_explicit_engineering_mode(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'Art rejected by user'):
                render_demo(Path(d) / 'bad-film')
            self.assertFalse((Path(d) / 'bad-film').exists())

    def test_internal_frame_api_remains_available_for_speech_and_rig_tests(self):
        svg = frame_svg(.5)
        self.assertIn('data-art-status="engineering-blockout"', svg)
        self.assertIn('mouth-rig', svg)
        self.assertIn('hand-L', svg)


if __name__ == '__main__':
    unittest.main()
