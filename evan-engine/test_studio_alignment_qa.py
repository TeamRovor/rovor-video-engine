import copy
import json
import math
import tempfile
from pathlib import Path
import struct
import unittest
import wave

from studio_alignment_qa import evaluate, _percentile

class AlignmentGateTests(unittest.TestCase):
    def fixture(self):
        return {'alignment':{'status':'acoustic'},
        'words':[{'word':'open','scriptIndex':0,'start':.2,'end':.6,'reviewFlags':['word-anchor-disagreement'],'acousticScore':-14},
                 {'word':'business','scriptIndex':1,'start':.61,'end':.9,'reviewFlags':[],'acousticScore':-6}],
        'estimatedWords':[{'scriptIndex':0,'start':.02,'end':.15},{'scriptIndex':1,'start':.6,'end':.91}],
        'phonemes':[{'scriptIndex':0,'start':.2,'end':.32,'phone':'OW'},
                  {'scriptIndex':0,'start':.32,'end':.4,'phone':'P'},
                  {'scriptIndex':0,'start':.4,'end':.6,'phone':'AH'},
                  {'scriptIndex':1,'start':.61,'end':.617,'phone':'B'},
                  {'scriptIndex':1,'start':.617,'end':.624,'phone':'IH'},
                  {'scriptIndex':1,'start':.624,'end':.631,'phone':'Z'},
                  {'scriptIndex':1,'start':.631,'end':.9,'phone':'N'}]}

    def test_single_observation_percentile(self):
        self.assertEqual(_percentile([.2],.95),.2)

    def test_eighteen_style_flags_are_never_auto_approved(self):
        report=evaluate(self.fixture())
        self.assertEqual(report['status'],'blocked')
        self.assertEqual(report['flaggedWordCount'],1)
        self.assertEqual(report['unresolvedWordCount'],1)
        self.assertIsNone(report['wavEvidence'])
        self.assertIsNone(report['referenceMetrics'])
        self.assertTrue(any('short-phones' in x for x in report['reviewRisks']))
        self.assertFalse(report['words'][0]['acousticScoreIsProbability'])

    def test_accept_needs_notes_revise_needs_recompilation(self):
        plan=self.fixture()
        review={'words':[{'scriptIndex':0,'reviewDecision':'accept','reviewerNotes':''}]}
        self.assertEqual(evaluate(plan,review=review)['unresolvedWordCount'],1)
        review['words'][0]['reviewerNotes']='inspected waveform and listened at two speeds'
        self.assertEqual(evaluate(plan,review=review)['unresolvedWordCount'],0)
        review['words'][0]['reviewDecision']='revise'
        self.assertEqual(evaluate(plan,review=review)['unresolvedWordCount'],1)

    def test_true_audio_and_manual_reference_metrics(self):
        plan=self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sample.wav'
            with wave.open(str(path),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
                f.writeframes(struct.pack('<'+'h'*16000,*([3000]*16000)))
            reference={'provenance':'human-annotated','words':[{'scriptIndex':0,'start':.19,'end':.6},{'scriptIndex':1,'start':.61,'end':.9}]}
            review={'words':[{'scriptIndex':0,'reviewDecision':'accept','reviewerNotes':'listened and inspected the reference waveform'}]}
            r=evaluate(plan,wav=path,reference=reference,review=review)
            self.assertEqual(r['status'],'reviewed-not-animation-approved')
            self.assertEqual(r['referenceMetrics']['boundaryCount'],4)
            self.assertEqual(r['referenceMetrics']['fractionBoundariesWithin50ms'],1)
            self.assertEqual(r['wavEvidence']['sampleRate'],16000)
            reference['provenance']='another-speech-model'
            with self.assertRaisesRegex(ValueError,'human-annotated'):evaluate(plan,wav=path,reference=reference)

    def test_structural_anomalies_and_fallback_protection(self):
        plan=self.fixture();plan['alignment']['status']='fallback'
        with self.assertRaisesRegex(ValueError,'Acoustic alignment is required'):evaluate(plan)
        plan=self.fixture();plan['phonemes'][0]['end']=1.2
        report=evaluate(plan)
        self.assertTrue(any('phone-outside-word' in x for x in report['structuralErrors']))

if __name__=='__main__':unittest.main()