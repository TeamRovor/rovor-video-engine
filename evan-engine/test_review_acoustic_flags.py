"""Synthetic audio tests; passing them does not validate Evan's real timing."""
import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from review_acoustic_flags import create_packet, word_review_rows


class AcousticReviewTests(unittest.TestCase):
    def fixture(self):
        return {
            'alignment': {'status':'acoustic'},
            'words':[
                {'word':'open','scriptIndex':0,'start':.08,'end':.41,'reviewFlags':['word-anchor-disagreement'],'acousticScore':-13},
                {'word':'the','scriptIndex':1,'start':.43,'end':.62,'reviewFlags':[]},
                {'word':'door','scriptIndex':2,'start':.64,'end':.9,'reviewFlags':['word-anchor-disagreement'],'acousticScore':-22}
            ],
            'estimatedWords':[
                {'scriptIndex':0,'start':.02,'end':.15},
                {'scriptIndex':1,'start':.42,'end':.6},
                {'scriptIndex':2,'start':.91,'end':1.08}
            ],
            'phonemes':[
                {'scriptIndex':0,'start':.08,'end':.20,'phone':'OW'},
                {'scriptIndex':0,'start':.20,'end':.30,'phone':'P'},
                {'scriptIndex':0,'start':.30,'end':.41,'phone':'AH'},
                {'scriptIndex':1,'start':.43,'end':.62,'phone':'DH'},
                {'scriptIndex':2,'start':.64,'end':.90,'phone':'D'}]
        }

    def test_review_never_auto_accepts_and_is_indexed(self):
        rows=word_review_rows(self.fixture(),expected=2)
        self.assertEqual([r['scriptIndex'] for r in rows],[0,2])
        self.assertEqual([r['reviewDecision'] for r in rows],['pending','pending'])
        self.assertEqual(rows[0]['phoneSequence'],['OW','P','AH'])
        self.assertAlmostEqual(rows[1]['maxBoundaryDifferenceSec'],.27)

    def test_fallback_refused_and_expected_count_fail_closed(self):
        p=self.fixture();p['alignment']['status']='fallback'
        with self.assertRaisesRegex(ValueError,'Requires an acoustic'):word_review_rows(p)
        with self.assertRaisesRegex(ValueError,'Expected 18'):word_review_rows(self.fixture(),expected=18)

    def test_evidence_packet_and_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); wav=root/'tone.wav'
            rate=16000;t=np.arange(rate*2)/rate
            # Silence in the middle, distinct from the voiced sections.
            pcm=(.3*np.sin(2*np.pi*240*t)*(np.abs(t-.5)>.08)*32767).astype('<i2')
            with wave.open(str(wav),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())
            packet=root/'out';create_packet(self.fixture(),wav,packet,expected=2)
            j=json.loads((packet/'review.json').read_text())
            self.assertEqual(j['status'],'awaiting-perceptual-review')
            self.assertEqual(len(list(packet.glob('*.png'))),2)
            self.assertTrue((packet/'review.csv').exists())
            self.assertIn('Neither method is ground truth',(packet/'REVIEW.md').read_text())


if __name__=='__main__':unittest.main()
