"""Tests of deterministic Moho Switch1 export; no Moho instance required."""
import json
import tempfile
import unittest
from pathlib import Path
from moho_exposure import exposure, moho_dat, gesture_rows, convert


class MohoExposureTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(exposure([],24,0),[(1,"rest")])
    def test_simple(self):
        keys=exposure([{"start":0,"end":.25,"value":"B"},
                       {"start":.25,"end":.5,"value":"A"}],24,.5)
        self.assertEqual(keys,[(1,"AE"),(7,"MBP"),(13,"rest")])
    def test_gap(self):
        self.assertEqual(exposure([{"start":.1,"end":.2,"value":"D"}],20,.35),
                         [(1,"rest"),(3,"open"),(5,"rest")])
    def test_merged_similar_shapes(self):
        x=[{"start":0,"end":.05,"value":"E"},{"start":.05,"end":.1,"value":"F"}]
        self.assertEqual(exposure(x,60,.1),[(1,"O"),(7,"rest")])
    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            exposure([{"start":0,"end":.3,"value":"A"},
                      {"start":.2,"end":.4,"value":"B"}])
    def test_invalid_symbol_rejected(self):
        with self.assertRaises(ValueError):
            exposure([{"start":0,"end":.2,"value":"Z"}])
    def test_invalid_interval_rejected(self):
        with self.assertRaises(ValueError):
            exposure([{"start":.3,"end":.2,"value":"B"}])
    def test_frame_count_and_end_rest(self):
        self.assertEqual(exposure([{"start":0,"end":.07,"value":"B"}],24,.07),
                         [(1,"AE"),(3,"rest")])
    def test_format(self):
        self.assertEqual(moho_dat([(1,"rest"),(11,"open")]),
                         "MohoSwitch1\n1 rest\n11 open\n")
    def test_gestures(self):
        self.assertEqual(gesture_rows([{"start":0,"end":1,"kind":"point"}]),
                         [(1,25,"point")])
    def test_export_from_json(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);mouth=root/"mouth.json";scene=root/"scene.json";out=root/"evan.dat"
            mouth.write_text(json.dumps({"mouthCues":[{"start":0,"end":.2,"value":"B"}]}))
            scene.write_text(json.dumps({"duration":.5,"gestures":[
                {"start":.1,"end":.3,"kind":"point"}]}))
            result=convert(mouth,scene,out,24)
            self.assertTrue(out.read_text().startswith("MohoSwitch1\n"))
            self.assertIn("gesture_sheet",result)
            self.assertIn("point",out.with_suffix(".gestures.csv").read_text())


if __name__=="__main__":
    unittest.main()
