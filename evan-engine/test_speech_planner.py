import unittest,tempfile,wave
from pathlib import Path
try:
 import numpy as np
 from speech_planner import build_plan,planned_weights,shape
except ImportError:
 np=None

@unittest.skipIf(np is None,'Optional painted dependencies')
class SpeechPlannerTests(unittest.TestCase):
 def plan(self,script='map five',recognized='map five',silent=False):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);path=Path(d.name)/'a.wav'
  with wave.open(str(path),'wb') as f:
   f.setparams((1,2,16000,0,'NONE','not compressed'))
   x=np.zeros(16000) if silent else .2*np.sin(np.arange(16000)*.1)
   f.writeframes((x*32767).astype('<i2').tobytes())
  transcript={'transcription':[{'text':w,'offsets':{'from':i*500,'to':(i+1)*500}} for i,w in enumerate(recognized.split())]}
  return build_plan(script,transcript,path,[],{'map':[['M','AE1','P']],'five':[['F','AY1','V']]})
 def test_script_contacts_and_timing(self):
  p=self.plan();self.assertEqual([x['value'] for x in p['phonemes']],list('ADAGCG'))
  self.assertEqual(p['coverage'],1);self.assertAlmostEqual(p['phonemes'][-1]['end'],1)
  self.assertTrue(all(a['end']<=b['start']+1e-8 for a,b in zip(p['phonemes'],p['phonemes'][1:])))
 def test_mismatch_is_reported_not_invented(self):
  p=self.plan('map unknown');self.assertEqual(p['coverage'],.5);self.assertTrue(p['warnings'])
 def test_silence_does_not_open_jaw(self):
  p=self.plan(silent=True);w=planned_weights(.2,p,[]);self.assertAlmostEqual(w[0],1)
 def test_energy_is_not_phone_identity(self):
  self.assertEqual(shape('P'),'A');self.assertEqual(shape('V'),'G');self.assertEqual(shape('UW1'),'F')
 def test_continuity(self):
  p=self.plan();samples=[planned_weights(t,p,[]) for t in np.arange(0,1,.001)]
  self.assertLess(np.abs(np.diff(samples,axis=0)).max(),.1)
