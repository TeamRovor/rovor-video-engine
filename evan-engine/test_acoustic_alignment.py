import unittest
try:
 import numpy as np
 from english_articulation import PHONE_CATALOG,phone_gestures,cartoon_controls
 from speech_planner import planned_weights
 from acoustic_alignment import upgrade_plan
except ImportError:np=None

@unittest.skipIf(np is None,'Optional painted dependencies')
class AcousticAnimationTests(unittest.TestCase):
 def plan(self,phone='P',value='A'):
  p=dict(start=.30,end=.36,phone=phone,value=value,word='test')
  return dict(alignment={'status':'acoustic'},phonemes=[p],gestures=phone_gestures([p]),audio={'step':.01,'energy':[.5]*100},fallbackCues=[])
 def test_english_inventory(self):
  self.assertEqual(len(PHONE_CATALOG),39)
  self.assertEqual(set(PHONE_CATALOG),set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW B CH D DH F G HH JH K L M N NG P R S SH T TH V W Y Z ZH'.split()))
 def test_diphthongs_move_without_new_phone(self):
  p=self.plan('AW','D');self.assertEqual([x['value'] for x in p['gestures']],['D','F'])
  self.assertAlmostEqual(p['gestures'][0]['end'],p['gestures'][1]['start'])
  self.assertEqual(p['gestures'][0]['phoneIndex'],p['gestures'][1]['phoneIndex'])
 def test_silent_contact_survives_energy_gate(self):
  p=self.plan();p['audio']['energy']=[0.]*100
  self.assertGreater(planned_weights(.33,p,[])[1],.95)
  self.assertEqual(planned_weights(.8,p,[])[0],1)
 def test_contact_timing_tracks_phone_not_word_start(self):
  p=self.plan();self.assertGreater(planned_weights(.33,p,[])[1],.95)
  self.assertLess(planned_weights(.1,p,[])[1],.01)
 def test_acoustic_curve_continuity(self):
  p=self.plan();w=np.array([planned_weights(t,p,[]) for t in np.arange(0,1,.001)])
  self.assertLess(np.abs(np.diff(w,axis=0)).max(),.07)
  self.assertTrue(np.allclose(w.sum(axis=1),1))
 def test_controls_are_bounded(self):
  for i in range(9):
   w=np.eye(9)[i];controls=cartoon_controls(w)
   self.assertTrue(all(0<=v<=1 for v in controls.values()))
 def test_rejected_alignment_reports_fallback(self):
  p={'coverage':0,'warnings':[]};r=upgrade_plan(p,'unused')
  self.assertEqual(r['alignment']['status'],'fallback');self.assertTrue(r['warnings'])

 def test_long_vowel_is_sustained(self):
  p=self.plan('AA','D');p['phonemes'][0].update(start=.2,end=.9);p['gestures']=phone_gestures(p['phonemes'])
  for t in (.3,.5,.8):self.assertGreater(planned_weights(t,p,[])[4],.7)
