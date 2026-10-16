"""Guard exposure semantics, timing and source-art integrity; not visual approval."""
import hashlib
from pathlib import Path
import tempfile
import unittest
try:
    from performance_study import speech, track, rig, SHAPES
except ImportError:
    rig = None

@unittest.skipIf(rig is None, "Pillow and NumPy required for opt-in study")
class PerformanceStudyTests(unittest.TestCase):
    def test_fast_bilabial_is_not_smoothed_away(self):
        cues=[{'start':0,'end':.2,'value':'D'},{'start':.2,'end':.23,'value':'A'},
              {'start':.23,'end':.4,'value':'C'}]
        self.assertEqual(speech(.2,cues)[1],0)
        self.assertEqual(speech(.229,cues)[1],0)
        self.assertGreater(speech(.29,cues)[1],0)
        self.assertEqual(speech(.5,cues),SHAPES['X'])

    def test_motion_holds_and_settles(self):
        keys=[(0,0),(.5,-2),(1,6),(1.5,0)]
        self.assertEqual(track(-1,keys),0)
        self.assertEqual(track(2,keys),0)
        self.assertEqual(track(1,keys),6)
        self.assertAlmostEqual(track(.75,keys),2)

    def test_build_preserves_sources_and_repairs_transparent_teeth(self):
        root=Path(__file__).resolve().parent.parent/'evan-character/v3-assets'
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.png')}
        with tempfile.TemporaryDirectory() as d:
            layers=rig(Path(d))
            self.assertEqual(layers['head'].getpixel((228,155))[3],255)
            self.assertEqual(len(list(Path(d).glob('mouth_*.svg'))),9)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.png')}
        self.assertEqual(before,after)

if __name__=='__main__': unittest.main()
