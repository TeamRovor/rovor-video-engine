"""Offline validation. Run: python3 -m unittest -v test_evan_engine.py"""
import json
import tempfile
from pathlib import Path
import unittest
from scene_planner import classify, generate_plan, validate_plan, clean_title
from animate_evan import make_scene, read_json


class DirectorTests(unittest.TestCase):
    def test_subjects(self):
        self.assertEqual(classify('Your business needs a favicon'), 'favicon')
        self.assertEqual(classify('How to post social media Reels'), 'social')
        self.assertEqual(classify('Set up an online store checkout'), 'store')
        self.assertEqual(classify('People use Google for search results'), 'search')
        self.assertEqual(classify('We set these up at Rovor Digital'), 'endcard')
    def test_no_false_topic(self):
        self.assertIsNone(classify('Here is something important'))
    def test_plan_coverage(self):
        segments=[{'start':0.,'end':4.,'text':'Your website matters'},
                  {'start':4.,'end':8.,'text':'Try better social media posts'},
                  {'start':8.,'end':12.,'text':'Tell customers about your store'}]
        visuals, gestures=generate_plan(segments,12.)
        self.assertEqual(visuals[0]['start'],0)
        self.assertEqual(visuals[-1]['end'],12.)
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(visuals,visuals[1:])))
        self.assertTrue(len(gestures)>0)
    def test_favicon_beat_order(self):
        segs=[{'start':0,'end':4,'text':'Ever see the browser globe on your website?'},
              {'start':4,'end':8,'text':'You may be missing a favicon'},
              {'start':8,'end':13,'text':'Your brand matters'},
              {'start':13,'end':17,'text':'That detail looks finished'},
              {'start':17,'end':20,'text':'Rovor Digital can help'}]
        plan,_=generate_plan(segs,20.)
        self.assertEqual([x['kind'] for x in plan],['browser','favicon','brand','endcard'])
    def test_manual_plan(self):
        plan=[{'kind':'browser','start':0,'end':3}, {'kind':'brand','start':3,'end':5}]
        self.assertEqual(validate_plan(plan,5.)[-1]['kind'],'brand')
    def test_manual_rejects_gaps(self):
        with self.assertRaises(ValueError):
            validate_plan([{'kind':'topic','start':1,'end':5}],5.)
    def test_manual_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            validate_plan([{'kind':'invented','start':0,'end':5}],5.)
    def test_scene_generation(self):
        transcript={'transcription':[{'text':'A favicon is the little icon','offsets':{'from':0,'to':2000}},
                                      {'text':'Contact Rovor','offsets':{'from':2000,'to':4000}}]}
        cues={'mouthCues':[{'start':0,'end':4,'value':'B'}]}
        scene=make_scene(transcript,cues,4)
        self.assertEqual(scene['duration'],4)
        self.assertIn('scenePlan',scene)
        self.assertIn('gestures',scene)
    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('not json')
            self.assertIsNone(read_json(p))
    def test_title_safety(self):
        self.assertLessEqual(len(clean_title('Long headline ' * 20)),30)


class ReferenceArtworkTests(unittest.TestCase):
    def test_character_poses_exist(self):
        root = Path(__file__).resolve().parent.parent / "evan-character" / "v3-assets"
        for name in ("neutral", "point", "present"):
            path = root / (name + ".png")
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_reference_mouth_shapes_exist(self):
        root = Path(__file__).resolve().parent.parent / "evan-character" / "v3-assets"
        for pose in ("neutral", "point", "present"):
            for mouth in ("rest", "AE", "O", "UW", "L", "FV", "MBP", "smile", "open"):
                self.assertTrue((root / (pose + "_" + mouth + ".png")).is_file())

    def test_original_reference_remains(self):
        ref = Path(__file__).resolve().parent.parent / "evan-character" / "references" / "evan-personality.png"
        self.assertTrue(ref.is_file())


class V4ImprovementTests(unittest.TestCase):
    def test_topic_cues_are_grounded(self):
        examples = {
            'Our website must be responsive on a mobile phone': 'mobile',
            'Your page speed affects visitors': 'speed',
            'Enable the HTTPS certificate': 'security',
            'Check your website analytics': 'analytics',
        }
        for speech, expected in examples.items():
            with self.subTest(speech=speech):
                self.assertEqual(classify(speech), expected)

    def test_no_unearned_brand_slide(self):
        segments=[{'start':0.0,'end':5.0,'text':'Here is the lesson'},
                  {'start':5.0,'end':11.0,'text':'And here is the explanation'}]
        scenes,_=generate_plan(segments,11.0)
        self.assertEqual([s['kind'] for s in scenes], ['topic'])

    def test_brand_asset_is_real_png(self):
        root=Path(__file__).resolve().parent.parent / 'evan-character' / 'brand'
        for tone in ('white','black'):
            self.assertEqual((root/f'rovor-mark-{tone}.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
        self.assertTrue((root/'source-original.png').exists())

    def test_v4_calibrated_sprites(self):
        root=Path(__file__).resolve().parent.parent / 'evan-character' / 'v4-assets'
        for pose in ('neutral','point','present'):
            for phoneme in ('rest','MBP','AE','O','open','UW','FV','L','smile'):
                self.assertEqual((root/f'{pose}_{phoneme}.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
        config=json.loads((root/'calibration.json').read_text())
        self.assertEqual(config['version'],4)
        self.assertEqual(set(config['poses']),{'neutral','point','present'})

    def test_storyboard_supports_new_visual_types(self):
        for kind in ('mobile','speed','security','analytics'):
            self.assertEqual(validate_plan([{'kind':kind,'start':0,'end':4}],4)[0]['kind'],kind)

if __name__=='__main__':unittest.main()
