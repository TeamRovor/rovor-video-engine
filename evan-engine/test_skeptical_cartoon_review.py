import copy,json,unittest
from pathlib import Path
import numpy as np
from skeptical_cartoon_review import skeptical_event,skeptical_brows

class SkepticalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
  cls.base=dict(leftRaise=0.,rightRaise=0.,leftTilt=0.,rightTilt=0.)
 def test_phrase_shift_and_fallback(self):
  e=skeptical_event(self.plan);self.assertEqual(e['scriptIndices'],list(range(18,24)))
  p=copy.deepcopy(self.plan)
  for w in p['words']:w['start']+=3;w['end']+=3
  for key in ['anticipate','arrive','hold','settle']:self.assertAlmostEqual(skeptical_event(p)[key],e[key]+3)
  p['words'][20]['word']='other';self.assertIsNone(skeptical_event(p));self.assertEqual(skeptical_brows(6,p,self.base),self.base)
 def test_hold_off_continuity_and_immutability(self):
  before=copy.deepcopy(self.plan);e=skeptical_event(self.plan)
  for t in [0,e['anticipate'],e['settle'],23]:self.assertEqual(skeptical_brows(t,self.plan,self.base),self.base)
  self.assertEqual(skeptical_brows(6.2,self.plan,self.base),dict(leftRaise=-2.,rightRaise=7.,leftTilt=-4.,rightTilt=-3.))
  values=[list(skeptical_brows(float(t),self.plan,self.base).values()) for t in np.arange(5,7.5,1/480)]
  self.assertLess(float(abs(np.diff(values,axis=0)).max()),.08)
  self.assertEqual(before,self.plan);self.assertEqual(self.base,dict(leftRaise=0.,rightRaise=0.,leftTilt=0.,rightTilt=0.))
 def test_invalid_cues(self):
  for t in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):skeptical_brows(t,self.plan,self.base)
  p=copy.deepcopy(self.plan);p['words'][23]['end']=0
  with self.assertRaises(ValueError):skeptical_event(p)

 def test_stronger_opt_in_is_bounded_shifted_and_rest_exact(self):
  original=copy.deepcopy(self.plan);base=dict(self.base,unrelated=.37)
  event=skeptical_event(self.plan)
  for t in [0,event['anticipate'],event['settle'],23]:
   self.assertEqual(skeptical_brows(t,self.plan,base,strong=True),base)
  self.assertEqual(skeptical_brows(6.2,self.plan,base,strong=True),
                   dict(leftRaise=-6.,rightRaise=8.,leftTilt=-7.,rightTilt=-1.,unrelated=.37))
  shifted=copy.deepcopy(self.plan)
  for w in shifted['words']:w['start']+=3;w['end']+=3
  values=[]
  for t in np.arange(5,7.5,1/480):
   c=skeptical_brows(float(t),self.plan,base,strong=True)
   moved=skeptical_brows(float(t)+3,shifted,base,strong=True)
   np.testing.assert_allclose(list(c.values()),list(moved.values()),atol=1e-12)
   self.assertEqual(c['unrelated'],.37)
   values.append([c[k] for k in self.base])
  self.assertLessEqual(float(abs(np.array(values)).max()),8.)
  self.assertLess(float(abs(np.diff(values,axis=0)).max()),.09)
  self.assertEqual(skeptical_brows(6,{'words':[]},base,strong=True),base)
  self.assertEqual(self.plan,original);self.assertEqual(base,dict(self.base,unrelated=.37))

if __name__=='__main__':unittest.main()
