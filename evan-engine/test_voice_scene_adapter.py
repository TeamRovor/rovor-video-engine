import json, tempfile, unittest, wave
from pathlib import Path
from voice_scene_adapter import validate_scene, sample_switches, export

SCENE={'duration':1.0,'mouthCues':[
    {'start':0.,'end':.15,'value':'X'},
    {'start':.15,'end':.40,'value':'A'},
    {'start':.40,'end':.70,'value':'F'},
    {'start':.70,'end':1.0,'value':'X'}]}

class VoiceSceneAdapterTests(unittest.TestCase):
    def test_frame_base_quantization_and_rest(self):
        keys,report=sample_switches(SCENE,24)
        self.assertEqual(keys[0]['frame'],1)
        self.assertEqual([x['shape'] for x in keys],['X','A','F','X'])
        self.assertFalse(report['phoneBoundariesVerified'])
        self.assertFalse(report['later18FlaggedRegionsReviewed'])
        self.assertFalse(report['productionReady'])
    def test_no_arbitrary_fixes_and_reject_bad_cues(self):
        bad=json.loads(json.dumps(SCENE));bad['mouthCues'][1]['start']=.22
        with self.assertRaises(ValueError):validate_scene(bad)
        bad=json.loads(json.dumps(SCENE));bad['mouthCues'][2]['value']='Z'
        with self.assertRaises(ValueError):validate_scene(bad)
        with self.assertRaises(ValueError):sample_switches(SCENE,23)
    def test_decoded_pcm_duration_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'voice.wav'
            with wave.open(str(f),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
                w.writeframes(b'\0\0'*16000)
            keys,report=sample_switches(SCENE,24,f)
            self.assertEqual(report['sourceAudio']['sampleRate'],16000)
            with self.assertRaises(ValueError):sample_switches({**SCENE,'duration':1.2},24,f)
            src=Path(td)/'scene.json';src.write_text(json.dumps(SCENE))
            data=export(src,Path(td)/'out',f)
            self.assertTrue((Path(td)/'out/evan-v3-unreviewed.dat').read_text().startswith('MohoSwitch1\n1 X\n'))
            self.assertEqual(data['switchKeyCount'],4)

if __name__=='__main__':unittest.main()