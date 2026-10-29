import copy,json,unittest
import numpy as np
from cartoon_body import ROOT
from definition_digit_curl import definition_curl_event,definition_curl_amount

class DefinitionDigitCueTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=json.loads((ROOT.parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_current_anchors_shift_and_immutability(self):
  p=copy.deepcopy(self.plan);e=definition_curl_event(p);self.assertEqual(e['scriptIndices'],[33,34]);np.testing.assert_allclose([e[k]for k in ['anticipate','arrive','hold','settle']],[10.73,11.03,11.41,11.75]);self.assertEqual(p,self.plan)
  for w in p['words']:w['start']+=2;w['end']+=2
  for k in ['anticipate','arrive','hold','settle']:self.assertAlmostEqual(definition_curl_event(p)[k],e[k]+2)
 def test_bounded_continuous_amount_and_fallback(self):
  amounts=[definition_curl_amount(t,self.plan)for t in np.arange(10.6,11.9,1/480)];self.assertGreaterEqual(min(amounts),0);self.assertLessEqual(max(amounts),.2);self.assertLess(float(abs(np.diff(amounts)).max()),.003)
  for t in [0,10.73,11.75,15,23]:self.assertEqual(definition_curl_amount(t,self.plan),0)
  p=copy.deepcopy(self.plan);p['words'][33]['word']='different';self.assertIsNone(definition_curl_event(p));self.assertEqual(definition_curl_amount(11,p),0)
 def test_invalid_times_and_order(self):
  for t in [float('nan'),float('inf')]:
   with self.assertRaises(ValueError):definition_curl_amount(t,self.plan)
  p=copy.deepcopy(self.plan);p['words'][33]['end']=10.9
  with self.assertRaises(ValueError):definition_curl_event(p)

if __name__=='__main__':unittest.main()
