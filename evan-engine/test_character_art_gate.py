import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from character_art_gate import DIRECTION_ID, WARDROBE, REQUIRED_LAYERS, inspect


class RegisteredCharacterArtworkTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.root = Path(self.d.name)
        concept = self.root / 'design.png'
        Image.new('RGBA', (100, 100), (255, 255, 255, 255)).save(concept)
        self.plan = {
            'schemaVersion': 1, 'directionId': DIRECTION_ID,
            'wardrobe': dict(WARDROBE),
            'canvas': {'width': 96, 'height': 96},
            'sourceConcept': {'path': 'design.png', 'sha256': hashlib.sha256(concept.read_bytes()).hexdigest()},
            'layers': {},
        }
        for i, name in enumerate(REQUIRED_LAYERS):
            path = self.root / (name + '.png')
            layer = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
            # Distinct alpha plates; no full-canvas composite or clipped outline.
            for x in range(12 + i % 7, 30 + i % 7):
                for y in range(14 + i % 6, 30 + i % 6):
                    layer.putpixel((x, y), (24 + i % 130, 38, 70, 255))
            layer.save(path)
            self.plan['layers'][name] = {
                'path': path.name, 'pivot': {'x': 23, 'y': 24},
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            }

    def test_registered_parts_pass_only_mechanical_gate(self):
        result = inspect(self.plan, self.root)
        self.assertEqual(result['registeredLayerCount'], len(REQUIRED_LAYERS))
        self.assertEqual(result['mechanicalStatus'], 'passed')
        self.assertFalse(result['visualApproved'])
        self.assertFalse(result['animationReady'])
        self.assertFalse(result['releaseReady'])

    def test_wrong_wardrobe_rejected(self):
        b = copy.deepcopy(self.plan)
        b['wardrobe']['shirt'] = 'hoodie'
        with self.assertRaisesRegex(ValueError, 'Wardrobe'):
            inspect(b, self.root)

    def test_missing_and_duplicate_parts_rejected(self):
        b = copy.deepcopy(self.plan)
        del b['layers']['upper-lip']
        with self.assertRaisesRegex(ValueError, 'Missing'):
            inspect(b, self.root)
        b = copy.deepcopy(self.plan)
        b['layers']['upper-lip'] = b['layers']['lower-lip']
        with self.assertRaisesRegex(ValueError, 'flattened'):
            inspect(b, self.root)

    def test_hand_pose_registration_and_identity(self):
        b = copy.deepcopy(self.plan)
        b['layers']['hand-left-point']['pivot']['x'] += 2
        with self.assertRaisesRegex(ValueError, 'wrist pivot'):
            inspect(b, self.root)
        b = copy.deepcopy(self.plan)
        copied = self.root / 'hand-left-point.png'
        original = (self.root / 'hand-left-relaxed.png').read_bytes()
        copied.write_bytes(original)
        b['layers']['hand-left-point']['sha256'] = hashlib.sha256(original).hexdigest()
        with self.assertRaisesRegex(ValueError, 'identical image'):
            inspect(b, self.root)

    def test_opaque_composite_or_rgb_rejected(self):
        b = copy.deepcopy(self.plan)
        path = self.root / 'head-base.png'
        Image.new('RGBA', (96, 96), (245, 245, 245, 255)).save(path)
        b['layers']['head-base']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Opaque'):
            inspect(b, self.root)
        Image.new('RGB', (96, 96), (0, 0, 0)).save(path)
        b['layers']['head-base']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'RGBA'):
            inspect(b, self.root)

    def test_edge_clip_and_bad_registration_rejected(self):
        b = copy.deepcopy(self.plan)
        path = self.root / 'head-base.png'
        im = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
        im.putpixel((0, 22), (255, 0, 0, 255))
        im.save(path)
        b['layers']['head-base']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'touches'):
            inspect(b, self.root)
        b = copy.deepcopy(self.plan)
        b['layers']['head-base']['pivot']['x'] = 200
        with self.assertRaisesRegex(ValueError, 'Pivot'):
            inspect(b, self.root)

    def test_path_escape_and_content_change_rejected(self):
        b = copy.deepcopy(self.plan)
        b['layers']['head-base']['path'] = '../../private.png'
        with self.assertRaisesRegex(ValueError, 'escapes'):
            inspect(b, self.root)
        b = copy.deepcopy(self.plan)
        b['layers']['head-base']['sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            inspect(b, self.root)


if __name__ == '__main__':
    unittest.main()