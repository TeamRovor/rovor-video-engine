"""Visual-layer structural tests; require Pillow only when explicitly run."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageStat
    from build_layered_character import build, split_pose, render_layers, POSES
except ImportError:
    Image = None


@unittest.skipIf(Image is None, "Pillow required for optional character-layer build")
class LayeredCharacterTests(unittest.TestCase):
    def setUp(self):
        self.source=Path(__file__).resolve().parent.parent/"evan-character"/"v3-assets"

    def test_three_approved_poses_reconstruct(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=build(self.source,d)
            self.assertEqual(set(manifest["poses"]),set(POSES))
            for name,meta in manifest["poses"].items():
                self.assertLess(meta["zero_tilt_rgb_mae"],1)
                self.assertEqual(meta["safe_tilt_degrees"],[-3,3])
                for key in ("head_image","body_image"):
                    self.assertTrue((Path(d)/meta[key]).is_file())

    def test_originals_are_untouched(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.source.glob("*.png")}
        with tempfile.TemporaryDirectory() as d:
            build(self.source,d)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.source.glob("*.png")}
        self.assertEqual(before,after)

    def test_head_tilt_changes_pixels_without_disturbing_body(self):
        original=Image.open(self.source/"neutral.png").convert("RGBA")
        body,head=split_pose(original,POSES["neutral"])
        a=render_layers(body,head,-3,POSES["neutral"]["pivot"])
        b=render_layers(body,head,3,POSES["neutral"]["pivot"])
        # upper head changed, pants are still pixel-identical between angles
        self.assertIsNotNone(ImageChops.difference(a.convert("RGB").crop((150,0,350,180)),
                                                    b.convert("RGB").crop((150,0,350,180))).getbbox())
        self.assertIsNone(ImageChops.difference(a.convert("RGB").crop((50,400,360,780)),
                                               b.convert("RGB").crop((50,400,360,780))).getbbox())


if __name__=="__main__":
    unittest.main()
