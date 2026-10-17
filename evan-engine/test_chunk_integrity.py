"""Render resume checks: never trust chunk existence alone."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from chunk_integrity import chunk_matches


class FakeCapture:
    def __init__(self, width=32, height=24, fps=60., count=3, decodable=3):
        self.width, self.height, self.fps = width, height, fps
        self.count, self.decodable, self.reads = count, decodable, 0
        self.released = False

    def isOpened(self):
        return True

    def get(self, prop):
        import cv2
        return {cv2.CAP_PROP_FRAME_WIDTH: self.width,
                cv2.CAP_PROP_FRAME_HEIGHT: self.height,
                cv2.CAP_PROP_FPS: self.fps,
                cv2.CAP_PROP_FRAME_COUNT: self.count}[prop]

    def read(self):
        self.reads += 1
        if self.reads > self.decodable:
            return False, None
        return True, np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def release(self):
        self.released = True


class ChunkIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'landscape-000.mp4'
        self.path.write_bytes(b'nonempty placeholder: mocked decoder')

    def check(self, reader):
        with patch('chunk_integrity.cv2.VideoCapture', return_value=reader):
            valid = chunk_matches(self.path, 3, (32, 24), 60)
        self.assertTrue(reader.released)
        return valid

    def test_fully_decoded_chunk_can_be_reused(self):
        self.assertTrue(self.check(FakeCapture()))

    def test_rejects_wrong_dimensions_and_fps(self):
        self.assertFalse(self.check(FakeCapture(width=64)))
        self.assertFalse(self.check(FakeCapture(fps=30)))

    def test_rejects_truncated_or_extra_frames(self):
        self.assertFalse(self.check(FakeCapture(decodable=2)))
        self.assertFalse(self.check(FakeCapture(count=4)))
        self.assertFalse(self.check(FakeCapture(decodable=4)))

    def test_rejects_missing_or_empty_video(self):
        self.path.unlink()
        self.assertFalse(chunk_matches(self.path, 3, (32, 24), 60))
        self.path.touch()
        self.assertFalse(chunk_matches(self.path, 3, (32, 24), 60))

    def test_bad_configuration_is_not_a_cache_miss(self):
        with self.assertRaises(ValueError):
            chunk_matches(self.path, 0, (32, 24), 60)
        with self.assertRaises(ValueError):
            chunk_matches(self.path, 3, (0, 24), 60)


if __name__ == '__main__':
    unittest.main()
