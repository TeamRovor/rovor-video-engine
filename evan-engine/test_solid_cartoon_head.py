"""Rendered regression for the neutral/UW brown blend, not an art acceptance test."""
import unittest
import numpy as np
from fv_cartoon_head import FVContactHead
from solid_cartoon_head import SolidCavityHead

class SolidCavityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=FVContactHead();cls.new=SolidCavityHead()
    def test_pure_poses_and_contacts_stay_exact(self):
        for w in np.eye(9):
            np.testing.assert_array_equal(np.asarray(self.new.weights(w)),np.asarray(self.old.weights(w)))
    def test_transition_changes_only_oral_pixels(self):
        for i in (3,4,5,6):
            w=np.zeros(9);w[0]=.5405;w[i]=.4595
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));a=a.copy();b=b.copy()
            a[300:385,180:295]=0;b[300:385,180:295]=0
            np.testing.assert_array_equal(a,b)
    def test_logo_transition_center_is_cavity_pigment_not_skin_mixture(self):
        w=np.zeros(9);w[0]=.5405;w[6]=.4595
        target=sum(self.new.points[s]*v for s,v in zip('XABCDEFGH',w));x,y=np.mean(target[16:32],axis=0).round().astype(int)
        before=np.asarray(self.old.weights(w))[y,x];after=np.asarray(self.new.weights(w))[y,x]
        self.assertGreater(int(before[1]),70)
        self.assertLess(int(after[1]),35)
        self.assertLess(int(after[1]),int(after[0])*.3)

    def test_weak_rounding_keeps_closed_ink_unbroken(self):
        w=np.zeros(9);w[0]=.9;w[6]=.1
        before=np.asarray(self.old.weights(w));after=np.asarray(self.new.weights(w))
        mask=np.zeros((512,512),bool);mask[309:340,190:285]=True
        mask&=before[:,:,:3].max(axis=2)<100
        self.assertGreater(int(mask.sum()),10)
        # Ink coverage must remain dark; tiny antialias color changes are valid.
        self.assertLess(int(after[:,:,:3][mask].max()),128)
    def test_narrow_oral_mesh_stays_noninverting(self):
        from cartoon_head import TRIANGLES,SYMBOLS
        ids=np.asarray(TRIANGLES)
        for i in range(9):
            for j in range(9):
                for v in np.linspace(0,1,13):
                    w=np.eye(9)[i]*(1-v)+np.eye(9)[j]*v
                    target=sum(self.new.points[s]*n for s,n in zip(SYMBOLS,w))
                    aperture=sum(n*(self.new.geometry[s][7]-self.new.geometry[s][6]) for s,n in zip(SYMBOLS,w))
                    tri=self.new.oral_target(target,aperture)[ids];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                    self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)

if __name__=='__main__':unittest.main()
