import tempfile,unittest
from pathlib import Path
from PIL import Image
from motion_dailies_qa import analyze_frames

class MotionDailyTests(unittest.TestCase):
    def test_frozen_and_black_frames_are_review_cues(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(15):Image.new('RGB',(32,24),(0,0,0)).save(d/f'{i:04d}.png')
            r=analyze_frames(d)
            self.assertEqual(len(r['blackFrameIndices']),15)
            self.assertTrue(r['longNearIdenticalRuns'])
            self.assertFalse(r['artisticApproval'])
    def test_declared_cut_not_jump_anomaly(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i in range(24):
                Image.new('RGB',(32,24),(255,0,0) if i<12 else (0,255,0)).save(d/f'{i:04d}.png')
            self.assertIn(12,analyze_frames(d)['unexplainedJumpFrameIndices'])
            self.assertNotIn(12,analyze_frames(d,cut_frames=[12])['unexplainedJumpFrameIndices'])
    def test_fail_closed_without_proof(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):analyze_frames(td)

if __name__=='__main__':unittest.main()