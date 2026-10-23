"""Offline frame-delta edge cases (no client media or network)."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'tools'/'video_version_delta_qa.py'
spec=importlib.util.spec_from_file_location('video_delta_qa',p)
video=importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)

class DeltaQaTests(unittest.TestCase):
    def test_identical_frames(self):
        res=video.compare([bytes([10,20,30])]*3,[bytes([10,20,30])]*3)
        self.assertEqual(res['near_identical_samples'],3)
        self.assertEqual(res['changed_intervals_inclusive'],[])
    def test_distinct_intervals_exact(self):
        a=[bytes([20])*18 for _ in range(9)]
        b=[bytes([20])*18 for _ in range(9)]
        for i in (1,2,6,7,8):b[i]=bytes([200])*18
        d=video.compare(a,b)
        self.assertEqual(d['changed_intervals_inclusive'],[[1,2],[6,8]])
        self.assertEqual(d['near_identical_samples'],4)
    def test_bounded_thresholds(self):
        for v in (0,-1,255,256):
            with self.subTest(v=v),self.assertRaises(ValueError):video.compare([b'\0'],[b'\0'],threshold=v)
    def test_length_fail_closed(self):
        with self.assertRaises(ValueError):video.frame_mae(b'abc',b'ab')
        with self.assertRaises(ValueError):video.compare([b'a'],[b'a',b'a'])
    def test_no_false_assertions(self):
        self.assertEqual(round(video.frame_mae(b'\0\0',b'\x01\0'),3),0.5)

if __name__=='__main__':unittest.main()