import copy,unittest
from production_shot_plan import compile_plan

SPEC={'schemaVersion':1,'source':'editorial-authored','characterStyle':'rovor-evan-expressive-cartoon','characterArtStatus':'awaiting-visual-approval','fps':24,
      'shots':[{'kind':'evan-host','purpose':'Opening premise','start':0,'end':1},
               {'kind':'rover-cutaway','purpose':'Visual brand worldbuilding','start':1,'end':2,'roverReferenceIds':['rovor-left-right-and-top','rovor-side-hero']}],
      'actingBeats':[{'at':.3,'intent':'skeptical reaction'}], 'delivery':{'safeLeftPct':.12,'safeRightPct':.12}}
class ShotPlanTests(unittest.TestCase):
    def test_realistic_timebase_and_not_art_ready(self):
        d=compile_plan(SPEC,{'durationSec':2,'wavSha256':'a'*64})
        self.assertEqual(d['totalFrames'],48)
        self.assertEqual(d['shotCount'],2)
        self.assertEqual(d['shots'][1]['startFrame'],24)
        self.assertFalse(d['renderReady'])
        self.assertFalse(d['voiceAlignmentVerified'])
        self.assertEqual(d['audioTailPadFrames'],0)
    def test_one_frame_tail_preserves_audio(self):
        shifted=copy.deepcopy(SPEC)
        shifted['shots'][-1]['end']=1.99
        d=compile_plan(shifted,{'durationSec':2.01})
        self.assertEqual(d['audioTailPadFrames'],1)
        self.assertEqual(d['shots'][-1]['endFrameExclusive'],49)
    def test_editorial_authority(self):
        for key,value in [('source','automatically-inferred'),('characterArtStatus','approved'),('characterStyle','hoodie')]:
            bad=copy.deepcopy(SPEC);bad[key]=value
            with self.assertRaises(ValueError):compile_plan(bad,{'durationSec':2})
        bad=copy.deepcopy(SPEC);bad['shots'][0]['audioRmsToGesture']=1
        with self.assertRaises(ValueError):compile_plan(bad,{'durationSec':2})
    def test_contiguity_and_grounded_rover(self):
        bad=copy.deepcopy(SPEC);bad['shots'][1]['start']=1.2
        with self.assertRaises(ValueError):compile_plan(bad,{'durationSec':2})
        bad=copy.deepcopy(SPEC);bad['shots'][1].pop('roverReferenceIds')
        with self.assertRaises(ValueError):compile_plan(bad,{'durationSec':2})

if __name__=='__main__':unittest.main()