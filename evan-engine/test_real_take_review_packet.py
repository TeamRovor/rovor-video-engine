import json
from pathlib import Path
import tempfile
import unittest
import wave
import numpy as np
from real_take_review_packet import audit

class ReviewPacketTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        x=(np.sin(2*np.pi*230*np.arange(16000)/16000)*9000).astype('<i2')
        self.wav=self.root/'a.wav'
        with wave.open(str(self.wav),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(x.tobytes())
        self.scene=self.root/'scene.json'
        self.data={'duration':1.0,'mouthCues':[{'start':0,'end':.5,'value':'A'},
                {'start':.5,'end':1.,'value':'X'}],
                'segments':[{'start':0,'end':1,'text':'test phrase'}]}
        self.scene.write_text(json.dumps(self.data))
    def test_real_audio_packet_is_review_only(self):
        out=audit(self.wav,self.scene,self.root/'out',plots=False)
        self.assertEqual(out['mouthCueCount'],2)
        self.assertFalse(out['humanPhonemeBoundariesVerified'])
        self.assertTrue((self.root/'out'/'cue-review.tsv').exists())
        self.assertNotIn('human-approved',str(out))
    def test_wrong_audio_checksum_fails(self):
        with self.assertRaisesRegex(ValueError,'checksum'):
            audit(self.wav,self.scene,self.root/'out',expected_pcm_sha256='0'*64,plots=False)
    def test_discontinuous_cues_fail(self):
        self.data['mouthCues'][1]['start']=.7;self.scene.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError,'discontinuous'):
            audit(self.wav,self.scene,self.root/'out',plots=False)
    def test_wrong_take_duration_fails(self):
        self.data['duration']=1.5;self.scene.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError,'duration'):
            audit(self.wav,self.scene,self.root/'out',plots=False)
    def test_no_silent_replacement(self):
        self.data['mouthCues'][0]['value']='F';self.scene.write_text(json.dumps(self.data))
        out=audit(self.wav,self.scene,self.root/'out',plots=False)
        self.assertFalse(out['releaseReady'])

if __name__=='__main__':unittest.main()