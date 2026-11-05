"""Independent lip-width/jaw controls; no phonetic or visual acceptance claim."""
import unittest,copy
import numpy as np
from rounded_cartoon_head import RoundedCartoonHead,rounding_identity
from speech_planner import acoustic_weights
from cartoon_head import SYMBOLS,TRIANGLES

def plan(energy=1.,phone='UW',symbol='F'):
    phones=[dict(start=0.,end=.4,phone=phone,value=symbol)]
    return dict(gestures=phones,phonemes=phones,audio=dict(energy=[energy]*100,step=.01),silences=[])

class RoundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.head=RoundedCartoonHead()
    def test_gain_changes_opening_but_not_pure_rounded_phone_width(self):
        targets=[];base=[]
        for energy in (.01,1.):
            p=plan(energy);jaw=acoustic_weights(.2,p,[]);shape=acoustic_weights(.2,p,[],energy_weighting=False)
            targets.append(self.head.target_points(jaw,shape));base.append(self.head.target_points(jaw))
        np.testing.assert_array_equal(targets[0][:32,0],targets[1][:32,0])
        self.assertGreater(float(np.max(abs(targets[0][:32,1]-targets[1][:32,1]))),5)
        self.assertGreater(float(np.max(abs(base[0][:32,0]-base[1][:32,0]))),5)
        for t,b in zip(targets,base):
            np.testing.assert_array_equal(t[:,1],b[:,1]);np.testing.assert_array_equal(t[32:],b[32:])
    def test_nonrounded_and_full_contacts_keep_target_exact(self):
        for phone,symbol in [('AA','D'),('M','A'),('F','G')]:
            p=plan(.01,phone,symbol);jaw=acoustic_weights(.2,p,[]);shape=acoustic_weights(.2,p,[],energy_weighting=False)
            np.testing.assert_array_equal(self.head.target_points(jaw,shape),self.head.target_points(jaw))
    def test_silence_returns_both_controls_to_rest(self):
        p=plan(.01);p['silences']=[dict(start=0.,end=.8)]
        for flag in (True,False):
            w=acoustic_weights(.2,p,[],energy_weighting=flag)
            np.testing.assert_allclose(w,np.eye(9)[0],atol=1e-8)
    def test_planner_does_not_mutate_reference(self):
        p=plan(.01);before=copy.deepcopy(p)
        acoustic_weights(.2,p,[],energy_weighting=False)
        self.assertEqual(p,before)
    def test_acoustic_target_and_oral_mesh_remain_noninverting(self):
        ids=np.asarray(TRIANGLES)
        for phone,symbol in [('UW','F'),('OW','E'),('L','H'),('M','A'),('F','G')]:
            for energy in (.01,.2,1.):
                p=plan(energy,phone,symbol)
                for t in np.linspace(0,.6,31):
                    jaw=acoustic_weights(t,p,[]);shape=acoustic_weights(t,p,[],energy_weighting=False)
                    target=self.head.target_points(jaw,shape);ap=sum(v*(self.head.geometry[s][7]-self.head.geometry[s][6]) for s,v in zip(SYMBOLS,jaw))
                    for points in (target,self.head.oral_target(target,ap)):
                        tri=points[ids];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                        self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)

    def test_shape_lead_release_reduces_peak_width_step(self):
        p=plan(.01);p['fallbackCues']=[]
        p['gestures'][0].update(start=.2,end=.6)
        raw=[];filtered=[]
        for t in np.arange(44)/48:
            jaw=acoustic_weights(t,p,[])
            identity=acoustic_weights(t,p,[],energy_weighting=False)
            for rows,shape in [(raw,identity),(filtered,rounding_identity(t,p))]:
                target=self.head.target_points(jaw,shape);rows.append(float(target[0,0]-target[8,0]))
        self.assertLess(float(np.max(abs(np.diff(filtered)))),float(np.max(abs(np.diff(raw))))*.8)
    def test_full_contact_blocks_future_rounding(self):
        shape=np.eye(9)[6]
        for i in (1,7):
            jaw=np.eye(9)[i]
            np.testing.assert_array_equal(self.head.target_points(jaw,shape),self.head.target_points(jaw))

    def test_rounding_does_not_pull_skin_marks_onto_cheek(self):
        from solid_cartoon_head import SolidCavityHead
        from PIL import Image
        jaw=np.zeros(9);jaw[0]=.5405;jaw[6]=.4595
        identity=np.zeros(9);identity[0]=.06;identity[6]=.94
        old=np.asarray(SolidCavityHead().weights(jaw));new=np.asarray(self.head.weights(jaw,shape_weights=identity))
        old=old.copy();new=new.copy();old[300:385,180:295]=0;new[300:385,180:295]=0
        np.testing.assert_array_equal(old,new)

if __name__=='__main__':unittest.main()
