import copy,unittest
import numpy as np
from speech_alignment_audit import spectrum,flagged_regions,energy_fraction

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
    def test_energy_is_measured_in_the_requested_interval(self):
        x=np.r_[np.zeros(16000),np.full(16000,.5)]
        self.assertEqual(energy_fraction(x,16000,[0,1]),1)
        self.assertEqual(energy_fraction(x,16000,[1,2]),0)
if __name__=='__main__':unittest.main()
