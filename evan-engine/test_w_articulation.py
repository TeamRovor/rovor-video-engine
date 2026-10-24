import copy,unittest,numpy as np
from english_articulation import phone_gestures
from speech_planner import acoustic_weights
from rounded_cartoon_head import rounding_identity

class WArticulationTests(unittest.TestCase):
 def plan(self,energy=.5):
  phones=[dict(start=.2,end=.7,phone='W',value='F',word='test')]
  return dict(phonemes=phones,gestures=phone_gestures(phones),audio=dict(step=.01,energy=[energy]*100),silences=[],fallbackCues=[])
 def test_rounding_survives_through_assigned_long_w_in_both_controls(self):
  p=self.plan();before=copy.deepcopy(p)
  for t in [.3,.45,.6]:
   self.assertGreater(acoustic_weights(t,p,[],energy_weighting=False)[6],.9)
   self.assertGreater(acoustic_weights(t,p,[])[6],.7)
   self.assertGreater(rounding_identity(t,p)[6],.85)
  self.assertEqual(p,before)
 def test_w_still_respects_explicit_silence_and_contacts(self):
  p=self.plan();p['silences']=[dict(start=.2,end=.7)]
  np.testing.assert_array_equal(acoustic_weights(.45,p,[]),np.eye(9)[0])
  for phone,symbol,index in [('P','A',1),('M','A',1),('F','G',7),('V','G',7)]:
   p=self.plan(0);p['phonemes'].append(dict(start=.3,end=.6,phone=phone,value=symbol,word='test'));p['gestures']=phone_gestures(p['phonemes'])
   self.assertGreater(acoustic_weights(.45,p,[])[index],.99 if symbol=='A' else .84)
 def test_short_w_enters_and_leaves_continuously_without_lingering(self):
  p=self.plan();p['phonemes'][0].update(start=.3,end=.4);p['gestures']=phone_gestures(p['phonemes'])
  values=np.array([acoustic_weights(t,p,[])for t in np.arange(0,.8,.001)])
  self.assertTrue(np.isfinite(values).all());np.testing.assert_allclose(values.sum(axis=1),1)
  self.assertLess(float(abs(np.diff(values,axis=0)).max()),.05)
  self.assertGreater(acoustic_weights(.35,p,[])[6],.65)
  self.assertEqual(acoustic_weights(.6,p,[])[0],1)

if __name__=='__main__':unittest.main()
