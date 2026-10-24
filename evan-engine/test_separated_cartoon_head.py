"""Independent articulator/jaw safeguards; no perceptual-quality acceptance."""
import copy,unittest
import numpy as np
from cartoon_head import SYMBOLS,TRIANGLES
from lingual_cartoon_head import LingualCartoonHead
from separated_cartoon_head import SeparatedCartoonHead,jaw_weights
from speech_planner import planned_weights
from rounded_cartoon_head import rounding_identity

def plan():
    phones=[dict(start=a,end=b,phone=p,value=s) for a,b,p,s in [(0,.2,'AH','C'),(.2,.3,'L','H'),(.3,.5,'OW','E'),(.5,.65,'M','A'),(.65,.85,'F','G'),(.85,1.1,'AA','D')]]
    return dict(alignment=dict(status='acoustic'),phonemes=phones,gestures=phones,fallbackCues=[],audio=dict(energy=[.1]*150,step=.01),silences=[dict(start=1.2,end=1.6)])

class SeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=LingualCartoonHead();cls.new=SeparatedCartoonHead()
    def test_contacts_normalization_and_nonmutation(self):
        p=plan();saved=copy.deepcopy(p)
        for t in np.arange(80)/48:
            w=planned_weights(t,p,[]);before=w.copy();jaw=jaw_weights(t,p,w)
            np.testing.assert_array_equal(w,before)
            np.testing.assert_array_equal(jaw[[1,7]],w[[1,7]])
            self.assertAlmostEqual(float(jaw.sum()),1,places=12);self.assertGreaterEqual(float(jaw.min()),0)
        self.assertEqual(p,saved)
    def test_settled_silence_is_exact(self):
        p=plan();np.testing.assert_array_equal(jaw_weights(1.4,p),np.eye(9)[0])
    def test_unaligned_fallback_render_is_exact(self):
        p=plan();p['alignment']['status']='fallback';p['words']=[]
        np.testing.assert_array_equal(self.old.at(.23,p),self.new.at(.23,p))
    def test_reduced_jaw_retains_strong_tongue_identity(self):
        p=plan();w=planned_weights(.23,p,[]);j=jaw_weights(.23,p,w)
        self.assertGreater(w[8],.7);self.assertLess(j[8],w[8]*.4)
        opening=lambda x:sum(v*(self.new.geometry[s][7]-self.new.geometry[s][6]) for s,v in zip(SYMBOLS,x))
        self.assertLess(opening(j),opening(w)*.8)
    def test_contact_and_default_pixels_remain_exact(self):
        for i in [0,1,7]:
            w=np.eye(9)[i]
            np.testing.assert_array_equal(self.old.weights(w),self.new.weights(w,geometry_weights=w))
    def test_tongue_can_change_without_changing_jaw_geometry(self):
        jaw=np.eye(9)[2]*.75+np.eye(9)[8]*.25
        lifted=np.asarray(self.new.weights(np.eye(9)[8],geometry_weights=jaw))
        lowered=np.asarray(self.new.weights(np.eye(9)[2],geometry_weights=jaw))
        mask=np.ones((512,512),bool);mask[300:385,180:295]=False
        np.testing.assert_array_equal(lifted[mask],lowered[mask])
        self.assertGreater(np.count_nonzero(lifted!=lowered),0)
    def test_smoothed_targets_do_not_invert_skin_or_oral_mesh(self):
        p=plan();ids=np.asarray(TRIANGLES)
        for t in np.arange(80)/48:
            j=jaw_weights(t,p);shape=rounding_identity(t,p)
            target=self.new.target_points(j,shape);ap=sum(v*(self.new.geometry[s][7]-self.new.geometry[s][6]) for s,v in zip(SYMBOLS,j))
            for points in [target,self.new.oral_target(target,ap),self.new.skin_target(j,target)]:
                tri=points[ids];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)
