"""Prevent 8-9min video renders filling the owner's Mac with giant body PNGs."""
import unittest
from render_acting_video import persist_body_frames


class CachePolicyTests(unittest.TestCase):
    def test_22s_development_study_can_reuse_legacy_cache(self):
        self.assertTrue(persist_body_frames("auto",22.047375))
    def test_production_videos_30s_plus_are_in_memory_by_default(self):
        for duration in (30,30.1,60,507.8726875,540,900):
            self.assertFalse(persist_body_frames("auto",duration))
    def test_opt_in_expensive_body_cache(self):
        self.assertTrue(persist_body_frames("on",540))
    def test_explicit_never_cache_to_disk(self):
        self.assertFalse(persist_body_frames("off",5))
    def test_invalid_inputs_fail(self):
        for bad in (0,-1,float("inf"),float("nan"),True):
            with self.assertRaises(ValueError):persist_body_frames("auto",bad)
        with self.assertRaises(ValueError):persist_body_frames("maybe",60)


if __name__=="__main__":unittest.main()
