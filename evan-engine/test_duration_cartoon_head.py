"""Duration/identity regressions, not physiological/perceptual acceptance."""
import json,unittest
from pathlib import Path
import cv2,numpy as np
from duration_cartoon_head import DurationCartoonHead,vowel_excursion,duration_budget,duration_jaw_weights
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from separated_cartoon_head import jaw_weights
from speech_planner import planned_weights
class DurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1);cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text());cls.old=CorrespondentFVCartoonHead();cls.new=DurationCartoonHead()
    def test_all_pure_controls_exact(self):
        for i in range(9):np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_excursion_is_bounded_monotone_and_long_vowels_exact(self):
        values=np.array([vowel_excursion(v) for v in np.linspace(.02,.4,101)])
        self.assertGreaterEqual(values.min(),.45);self.assertLessEqual(values.max(),1);self.assertTrue(np.all(np.diff(values)>=0));self.assertEqual(vowel_excursion(.3),1)
    def test_contacts_rest_and_normalization_preserved(self):
        for i in range(489):
            t=i/48;identity=planned_weights(t,self.plan,self.plan['fallbackCues']);old=jaw_weights(t,self.plan,identity);new=duration_jaw_weights(t,self.plan,identity)
            np.testing.assert_array_equal(new[[0,1,5,6,7,8]],old[[0,1,5,6,7,8]]);self.assertAlmostEqual(new.sum(),1);self.assertGreaterEqual(new.min(),0)
    def test_short_favicon_vowel_has_smaller_excursion(self):
        t=416/48;old=jaw_weights(t,self.plan);new=duration_jaw_weights(t,self.plan)
        aperture=lambda w:sum(v*(self.old.geometry[k][7]-self.old.geometry[k][6]) for k,v in zip('XABCDEFGH',w))
        self.assertLess(aperture(new),aperture(old)*.75);self.assertLess(duration_budget(t,self.plan),.6)
    def test_long_vowel_and_unaligned_fallback_unchanged(self):
        self.assertEqual(duration_budget(.15,dict(phonemes=[dict(start=0,end=.3,value='D',phone='AA')])),1)
        p=dict(self.plan);p['alignment']={'status':'rejected'}
        np.testing.assert_array_equal(duration_jaw_weights(416/48,p),jaw_weights(416/48,p))
if __name__=='__main__':unittest.main()
