"""Regression tests for 60-fps English phone/viseme metadata gating."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from speech_plan_gate import PHONE_TO_SHAPE, audit, frames_sampled, main, wav_duration


def plan():
    # "phone": pronounced /F OW N/, not its five written letters.
    return {'script':'phone', 'alignment': {'status': 'acoustic', 'wordCoverage': 1.0},
            'words': [{'start': .1, 'end': .70, 'scriptIndex': 0,
                       'word': 'phone', 'reviewFlags': []}],
            'phonemes': [
                {'start': .1, 'end': .2, 'scriptIndex': 0, 'word': 'phone','phone':'F','value':'G'},
                {'start': .2, 'end': .5, 'scriptIndex': 0, 'word': 'phone','phone':'OW1','value':'E'},
                {'start': .5, 'end': .7, 'scriptIndex': 0, 'word': 'phone','phone':'N','value':'B'}],
            'silences': []}


class SpeechGateTests(unittest.TestCase):
    def test_real_pronunciation_not_spelling(self):
        r = audit(plan(), 1., 60)
        self.assertEqual(r['status'], 'technical_pass_pending_visual_review')
        self.assertEqual(r['phoneCount'], 3)
        self.assertEqual(r['firstTargetCounts'], {'G':1, 'E':1, 'B':1})
        self.assertFalse(r['artisticApproval'])

    def test_mapped_english_contacts_and_diphthongs(self):
        self.assertEqual(len(PHONE_TO_SHAPE),39)
        self.assertEqual([PHONE_TO_SHAPE[x] for x in ('P','B','M','F','V','TH','DH','L')],
                         ['A','A','A','G','G','H','H','H'])
        self.assertEqual([PHONE_TO_SHAPE[x] for x in ('AY','OW','UW')],['C','E','F'])

    def test_spelling_letters_cannot_be_acoustic_phones(self):
        p = plan();p['phonemes'][0]['phone'] = 'PH'
        r = audit(p, 1.)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('unsupported phoneme', ' '.join(r['errors']))

    def test_script_missing_or_different_fails_closed(self):
        p=plan();del p['script']
        self.assertEqual(audit(p,1.)['status'],'blocked')
        p=plan();p['script']='phony'
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_word_index_gaps_and_overlaps_block(self):
        p=plan();p['words'][0]['scriptIndex']=2
        for ph in p['phonemes']:ph['scriptIndex']=2
        self.assertEqual(audit(p,1.)['status'],'blocked')
        p=plan()
        p['script']='phone now'
        p['words'].append({'start':.60,'end':.95,'scriptIndex':1,'word':'now','reviewFlags':[]})
        p['phonemes'].append({'start':.73,'end':.90,'scriptIndex':1,'word':'now','phone':'N','value':'B'})
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_fallback_cannot_be_certified(self):
        p=plan();p['alignment']={'status':'fallback'}
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_wrong_viseme_or_hallucinated_sound_blocks(self):
        p=plan();p['phonemes'][0]['value']='A'
        self.assertEqual(audit(p,1.)['status'],'blocked')
        p=plan();p['phonemes'][0]['phone']='XYZ'
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_wrong_word_boundaries_fail_closed(self):
        p=plan();p['phonemes'][1]['end']=.84
        self.assertEqual(audit(p,1.)['status'],'blocked')
        p=plan();p['phonemes'][1]['scriptIndex']=99
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_unsampled_contact_is_flagged_not_claimed_correct(self):
        p=plan();p['phonemes'][0].update(start=.001,end=.006)
        p['words'][0]['start']=0.
        r=audit(p,1.)
        self.assertEqual(r['status'],'review_required')
        self.assertEqual(r['unsampledContactCount'],1)
        self.assertFalse(r['artisticApproval'])
        self.assertEqual(frames_sampled(.001,.006,60),0)
        self.assertEqual(frames_sampled(.001,.020,60),1)

    def test_unreviewed_word_blocks_automatic_technical_acceptance(self):
        p=plan();p['words'][0]['reviewFlags']=['word-anchor-disagreement']
        r=audit(p,1.)
        self.assertEqual(r['status'],'review_required')
        self.assertEqual(r['reviewFlags'][0]['type'],'unreviewed-acoustic-word')

    def test_bad_duration_and_bool_rejected(self):
        for bad in (0, -1, float('nan'), True, 5000):
            with self.assertRaises(ValueError):
                audit(plan(),bad)
        p=plan();p['phonemes'][0]['start']=False
        self.assertEqual(audit(p,1.)['status'],'blocked')

    def test_audio_header_only_is_not_perceptual_approval(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'clean.wav'
            with wave.open(str(path),'wb') as f:
                f.setparams((1,2,16000,0,'NONE','not compressed'))
                f.writeframes(b'\x00\x00'*16000)
            self.assertEqual(wav_duration(path),1.)
            report=audit(plan(),wav_duration(path),wav_header_checked=True)
            self.assertEqual(report['provenance'],'source-WAV header read')
            self.assertFalse(report['artisticApproval'])

    def test_cli_report_does_not_change_plan(self):
        with tempfile.TemporaryDirectory() as d:
            inp=Path(d)/'plan.json';out=Path(d)/'report.json'
            original=json.dumps(plan());inp.write_text(original)
            import contextlib,io
            with contextlib.redirect_stdout(io.StringIO()):
                code=main(['--plan',str(inp),'--duration','1','--out',str(out)])
            self.assertEqual(code,0)
            self.assertEqual(inp.read_text(),original)
            self.assertEqual(json.loads(out.read_text())['status'],'technical_pass_pending_visual_review')


if __name__ == '__main__':
    unittest.main()
