"""Opt-in vowel glides preserve original recorded phone bounds and contacts."""
import copy
import unittest

import numpy as np
from continuous_diphthong import PROFILE, glide_strengths, prepare_glides
from english_articulation import PHONE_CATALOG, phone_gestures
from speech_planner import planned_weights


def synthetic_plan():
    phones=[
        dict(start=.2,end=.8,phone='OW1',value='E',word='phone',scriptIndex=0),
        dict(start=.9,end=.96,phone='P',value='A',word='pop',scriptIndex=1)
    ]
    gestures=phone_gestures(phones)
    return dict(alignment={'status':'acoustic'},phonemes=phones,gestures=gestures,
                audio={'step':.01,'energy':[.55]*200},fallbackCues=[],silences=[])


def enabled(plan):
    plan=copy.deepcopy(plan)
    plan['coarticulationProfile']=PROFILE
    plan['continuousGlides']=prepare_glides(plan['phonemes'],plan['gestures'])
    return plan


class ContinuousVowelGlideTests(unittest.TestCase):
    def test_supported_english_diphthongs_and_unchanged_acoustic_bounds(self):
        for phone,expected in [('AW',('D','F')),('AY',('C','B')),('EY',('C','B')),
                               ('OW',('E','F')),('OY',('E','B'))]:
            p={'phone':phone+'1','start':.10,'end':.65,'value':expected[0]}
            rows=prepare_glides([p],phone_gestures([p]))
            self.assertEqual(rows[0]['targets'],list(expected))
            self.assertEqual((rows[0]['start'],rows[0]['end']),(.10,.65))
            self.assertEqual([(x['start'],x['end']) for x in phone_gestures([p])],
                             [(.1,.375),(.375,.65)])

    def test_no_fake_word_phoneme_or_warping_audio_timing(self):
        plan=synthetic_plan()
        stored=copy.deepcopy(plan)
        changed=enabled(plan)
        self.assertEqual(plan,stored)
        self.assertEqual([x['phone'] for x in changed['phonemes']],['OW1','P'])
        self.assertEqual([(x['start'],x['end']) for x in changed['phonemes']],
                         [(.2,.8),(.9,.96)])
        self.assertEqual(len(changed['gestures']),len(plan['gestures']))

    def test_glide_carries_one_sustained_vowel_at_60fps(self):
        p=enabled(synthetic_plan())
        samples=[planned_weights(i/60,p,[]) for i in range(12,49)]
        for w in samples:
            self.assertAlmostEqual(float(sum(w)),1.,places=6)
            self.assertTrue(np.isfinite(w).all())
            self.assertTrue((w>=0).all())
        # At center a diphthong must not open a false silence between its two paints.
        middle=planned_weights(.5,p,[])
        # With synthetic audio energy .55, the existing RMS gate intentionally
        # reduces articulation to about 79.7%, including legacy vowel poses.
        # Test sustained relative strength instead of imposing a false 80% floor.
        activity=[float(planned_weights(t,p,[])[5:7].sum()) for t in (.35,.45,.5,.55,.65)]
        self.assertGreater(min(activity),.78)
        self.assertLess(max(activity)-min(activity),.015)
        self.assertLess(float(middle[0]),.22)
        early=planned_weights(.34,p,[])
        late=planned_weights(.68,p,[])
        self.assertGreater(float(early[5]),float(early[6]))
        self.assertGreater(float(late[6]),float(late[5]))

    def test_complementary_glide_strength_and_motion_continuity(self):
        a,b=.2,.8
        for t in np.arange(.0,1,.001):
            first,second=glide_strengths(float(t),a,b)
            self.assertGreaterEqual(first,0)
            self.assertGreaterEqual(second,0)
            self.assertLessEqual(first+second,1+1e-9)
        raw=np.array([glide_strengths(i/60,a,b) for i in range(60)])
        self.assertLess(float(np.max(np.abs(np.diff(raw,axis=0)))),.48)
        self.assertAlmostEqual(sum(glide_strengths(.5,a,b)),1,delta=.02)
        self.assertAlmostEqual(sum(glide_strengths(.1,a,b)),0,delta=1e-9)
        self.assertAlmostEqual(sum(glide_strengths(.95,a,b)),0,delta=1e-9)

    def test_very_short_vowel_has_bounded_six_frame_shape_transition(self):
        # A 55ms vowel is shorter than four 60fps frames. Its onset and end
        # remain the same, but the two painted shapes should not snap.
        p={'phone':'AY1','start':.2,'end':.255,'value':'C'}
        glides=prepare_glides([p],phone_gestures([p]))
        self.assertEqual(len(glides),1)
        self.assertEqual((glides[0]['start'],glides[0]['end']),(.2,.255))
        samples=np.array([glide_strengths(t,.2,.255) for t in np.arange(.15,.30,1/60)])
        self.assertTrue(np.isfinite(samples).all())
        self.assertTrue((samples>=0).all())
        self.assertGreater(float(samples.sum(axis=1).max()),.05)
        self.assertLess(float(np.max(np.abs(np.diff(samples,axis=0)))),.5)

    def test_multiple_phone_lengths_keep_frame_motion_bounded(self):
        for duration in (.012,.018,.025,.033,.055,.075,.10,.15,.30,.60):
            with self.subTest(seconds=duration):
                sampled=np.array([glide_strengths(t,.2,.2+duration)
                                  for t in np.arange(.0,1.05,1/60)])
                self.assertTrue(np.isfinite(sampled).all())
                self.assertLessEqual(float(sampled.sum(axis=1).max()),1.0000001)
                # Bound visible animation steps, not acoustic word timing.
                self.assertLess(float(np.max(np.abs(np.diff(sampled,axis=0)))),.42)

    def test_no_change_to_bilabial_contact_or_outside_glide(self):
        p=synthetic_plan();new=enabled(p)
        for t in (.01,.13,.87,.90,.92,.93,.95,1.09):
            np.testing.assert_allclose(planned_weights(t,p,[]),
                                       planned_weights(t,new,[]),atol=1e-7,rtol=0)
        self.assertGreater(float(planned_weights(.93,new,[])[1]),.95)

    def test_legacy_plan_weight_sequence_unchanged(self):
        p=synthetic_plan();same=copy.deepcopy(p)
        same['coarticulationProfile']='legacy'
        for t in np.arange(.0,1.10,.01):
            np.testing.assert_array_equal(planned_weights(float(t),p,[]),
                                          planned_weights(float(t),same,[]))

    def test_reject_unmatched_half_phoneme_metadata(self):
        p=synthetic_plan()
        p['gestures'][1]['end']+=.01
        with self.assertRaisesRegex(ValueError,'phase metadata'):
            prepare_glides(p['phonemes'],p['gestures'])

    def test_single_pose_vowels_are_not_invented_diphthongs(self):
        for phone in ('AE1','AH0','UW1','IH0'):
            p={'phone':phone,'start':.2,'end':.5,'value':PHONE_CATALOG[phone.rstrip('012')]['targets'][0]}
            self.assertEqual(prepare_glides([p],phone_gestures([p])),[])


if __name__=='__main__':
    unittest.main()
