import copy,unittest
import numpy as np
from speech_alignment_audit import spectrum,flagged_regions,energy_fraction,phone_audio_support

class SpeechAuditTests(unittest.TestCase):
    def test_fft_windows_stay_on_recording_sample_clock(self):
        rate=16000;x=np.zeros(16000);x[8000]=1
        db,times,freq=spectrum(x,rate,start_sample=32000)
        self.assertAlmostEqual(times[0],2+199.5/rate)
        # A transient must not be stretched toward either plot endpoint.
        peak=int(np.argmax(np.sum(10**(db/20),axis=0)))
        self.assertLess(abs(times[peak]-2.5),.006)
        self.assertLess(times[-1],3-.012)
    def test_review_contains_both_disagreeing_hypotheses(self):
        p=dict(words=[dict(word='test',scriptIndex=0,start=2,end=2.4,reviewFlags=['word-anchor-disagreement'])],estimatedWords=[dict(word='test',scriptIndex=0,start=1,end=1.4)])
        before=copy.deepcopy(p);rows,groups=flagged_regions(p,4)
        self.assertLess(groups[0]['start'],1);self.assertGreater(groups[0]['end'],2.4)
        self.assertEqual(p,before);self.assertEqual(rows[0]['boundaryStatus'],'unresolved')
    def test_long_phone_quiet_run_is_diagnostic_and_does_not_retime(self):
        p=[dict(start=.1,end=.5,word='way',phone='W',scriptIndex=0)]
        before=copy.deepcopy(p);x=np.full(16000,.2);x[3200:4800]=0
        rows=phone_audio_support(p,x,16000)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['lowEnergyRun'],[.2,.3]);self.assertEqual(p,before)
        self.assertFalse(rows[0]['timingChanged']);self.assertEqual(rows[0]['boundaryStatus'],'unresolved')
        self.assertEqual(phone_audio_support(p,np.full(16000,.2),16000),[])
        self.assertEqual(phone_audio_support([dict(p[0],end=.3)],x,16000),[])
    def test_upgrade_exposes_phone_audio_flags_without_changing_animation(self):
        from unittest.mock import patch
        from acoustic_alignment import upgrade_plan
        from speech_planner import planned_weights
        phone=dict(start=.1,end=.5,word='way',phone='W',value='F',scriptIndex=0)
        aligned=dict(words=[dict(word='way',scriptIndex=0,start=.1,end=.5,reviewFlags=[])],phonemes=[phone],silences=[],warnings=[],method='fixture',confidenceNote='not calibrated')
        plan=dict(coverage=1,words=[],phonemes=[],warnings=[],audio=dict(step=.01,energy=[.2]*100))
        with patch('acoustic_alignment.align_script',return_value=aligned),patch('speech_alignment_audit.read_audio',return_value=(np.zeros(16000),16000)):
            result=upgrade_plan(plan,'unused')
        self.assertEqual(result['alignment']['reviewWordCount'],1)
        self.assertIn('long-phone-low-energy-run',result['words'][0]['reviewFlags'])
        self.assertEqual(result['phonemes'],[phone])
        clean=copy.deepcopy(result);clean.pop('phoneAudioReview');clean['words'][0]['reviewFlags']=[]
        np.testing.assert_array_equal(planned_weights(.3,result,[]),planned_weights(.3,clean,[]))
    def test_short_vowel_quiet_prefix_reaches_review_without_retiming(self):
        from unittest.mock import patch
        from acoustic_alignment import upgrade_plan
        from speech_planner import planned_weights
        phone=dict(start=.1,end=.29,word='all',phone='AO1',value='E',scriptIndex=0)
        before=copy.deepcopy(phone);x=np.full(16000,.2);x[1600:2320]=0
        rows=phone_audio_support([phone],x,16000)
        self.assertEqual(rows[0]['flag'],'vowel-leading-low-energy-run');self.assertEqual(rows[0]['lowEnergyRun'],[.1,.145]);self.assertEqual(phone,before)
        self.assertEqual(phone_audio_support([dict(phone,phone='M')],x,16000),[])
        self.assertEqual(phone_audio_support([phone],np.zeros(16000),16000),[])
        x[2160:2320]=.2;self.assertEqual(phone_audio_support([phone],x,16000),[])
        x[2160:2320]=0
        aligned=dict(words=[dict(word='all',scriptIndex=0,start=.1,end=.29,reviewFlags=[])],phonemes=[phone],silences=[],warnings=[],method='fixture',confidenceNote='not calibrated')
        plan=dict(coverage=1,words=[],phonemes=[],warnings=[],audio=dict(step=.01,energy=[.2]*100))
        with patch('acoustic_alignment.align_script',return_value=aligned),patch('speech_alignment_audit.read_audio',return_value=(x,16000)):
            result=upgrade_plan(plan,'unused')
        self.assertIn('vowel-leading-low-energy-run',result['words'][0]['reviewFlags']);self.assertEqual(result['alignment']['reviewWordCount'],1);self.assertEqual(result['phonemes'],[before])
        clean=copy.deepcopy(result);clean.pop('phoneAudioReview');clean['words'][0]['reviewFlags']=[]
        np.testing.assert_array_equal(planned_weights(.2,result,[]),planned_weights(.2,clean,[]))
    def test_phone_flag_without_independent_anchor_stays_explicitly_unresolved(self):
        p=dict(words=[dict(word='way',scriptIndex=0,start=.1,end=.5,reviewFlags=['long-phone-low-energy-run'])],estimatedWords=[])
        rows,groups=flagged_regions(p,1)
        self.assertIsNone(rows[0]['anchor']);self.assertEqual(rows[0]['boundaryStatus'],'unresolved')
        self.assertLess(groups[0]['start'],.1);self.assertGreater(groups[0]['end'],.5)
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        import wave
        from speech_alignment_audit import audit
        with TemporaryDirectory() as folder:
            wav=Path(folder)/'voice.wav'
            with wave.open(str(wav),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(bytes(32000))
            with patch('speech_alignment_audit.plot_group'):
                report=audit(dict(p,phonemes=[]),wav,Path(folder)/'review')
            self.assertIsNone(report['words'][0]['anchorOutsideRecording'])
            self.assertIsNone(report['words'][0]['lowEnergyFractionBelowMinus40dBFS']['anchor'])
    def test_review_clips_preserve_exact_pcm_and_source_channels(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        import wave,hashlib
        from speech_alignment_audit import audit
        for channels in [1,2]:
            with self.subTest(channels=channels),TemporaryDirectory() as folder:
                p=Path(folder);samples=np.resize(np.array([-32768,-32767,-1,0,1,32767],dtype='<i2'),16000*channels).reshape(16000,channels);raw=samples.tobytes();wav=p/'voice.wav'
                with wave.open(str(wav),'wb') as f:
                    f.setnchannels(channels);f.setsampwidth(2);f.setframerate(16000);f.writeframes(raw)
                plan=dict(words=[dict(word='test',scriptIndex=0,start=.2,end=.7,reviewFlags=['word-anchor-disagreement'])],estimatedWords=[],phonemes=[]);before=copy.deepcopy(plan)
                with patch('speech_alignment_audit.plot_group'):report=audit(plan,wav,p/'review')
                g=report['regions'][0];first,last=g['audioSamples'];expected=raw[first*channels*2:last*channels*2]
                with wave.open(str(p/'review'/g['audio'])) as f:
                    self.assertEqual(f.getnchannels(),channels);self.assertEqual(f.getnframes(),last-first);self.assertEqual(f.readframes(f.getnframes()),expected)
                self.assertEqual(g['audioPcmSha256'],hashlib.sha256(expected).hexdigest());self.assertTrue(g['originalPcmPreserved']);self.assertEqual(plan,before)
    def test_energy_is_measured_in_the_requested_interval(self):
        x=np.r_[np.zeros(16000),np.full(16000,.5)]
        self.assertEqual(energy_fraction(x,16000,[0,1]),1)
        self.assertEqual(energy_fraction(x,16000,[1,2]),0)
if __name__=='__main__':unittest.main()
