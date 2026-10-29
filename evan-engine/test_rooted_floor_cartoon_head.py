"""Tongue root/pose/lip-occlusion regressions, not phonetic acceptance."""
import unittest
import cv2,numpy as np
from rooted_floor_cartoon_head import RootedFloorCartoonHead,rooted_blade_matrix
from duration_cartoon_head import DurationCartoonHead
from lingual_cartoon_head import tongue_matrix
class RootedFloorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.new=RootedFloorCartoonHead();cls.old=DurationCartoonHead()
    def oral(self,index):
        w=np.eye(9)[index];t=self.new.target_points(w);aperture=sum(v*(self.new.geometry[k][7]-self.new.geometry[k][6]) for k,v in zip('XABCDEFGH',w));return w,self.new.oral_target(t,aperture)
    def test_root_fixed_and_full_lift_source_matrix_exact(self):
        root=np.array([237,354,1],np.float32)
        for lift in np.linspace(0,1,21):np.testing.assert_allclose(rooted_blade_matrix(lift)@root,root[:2],atol=1e-4)
        np.testing.assert_array_equal(rooted_blade_matrix(1),tongue_matrix(1));self.assertLess(rooted_blade_matrix(0)[1,1],tongue_matrix(0)[1,1])
    def test_floor_covers_retracted_vowel_blade(self):
        w,oral=self.oral(4);blade,floor=self.new.tongue_parts(w,oral);exposed=blade[:,:,3]*(1-floor[:,:,3]/255)
        self.assertLess(float(exposed.sum()),float(blade[:,:,3].sum())*.15)
        mixed=self.new.tongue_surface(w,oral);opaque=floor[:,:,3]>=255
        np.testing.assert_array_equal(mixed[opaque],floor[opaque])
    def test_contact_tip_still_exposed(self):
        w,oral=self.oral(8);blade,floor=self.new.tongue_parts(w,oral);exposed=blade[:,:,3]*(1-floor[:,:,3]/255)
        self.assertGreater(float(exposed.sum()/255),20)
    def test_rest_bilabial_and_fv_controls_exact(self):
        for i in [0,1,7]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_tongue_remains_inside_matte_and_behind_teeth(self):
        class SilentTongue(RootedFloorCartoonHead):
            def tongue_surface(self,w,oral,shape_weights=None):return np.zeros((512,512,4),np.float32)
        w,oral=self.oral(8);cavity=self.new.cavity_surface(w,oral);mask=self.new.interior_mask(cavity,w,oral)[:,:,0]
        a=np.asarray(self.new.weights(w));b=np.asarray(SilentTongue().weights(w));changed=np.any(a!=b,axis=2)
        self.assertGreater(int(changed.sum()),0);self.assertEqual(int((changed&(mask==0)).sum()),0)
        teeth=self.new.teeth_surface(w,oral)*mask[:,:,None];np.testing.assert_array_equal(a[teeth[:,:,3]>=255],b[teeth[:,:,3]>=255])
if __name__=='__main__':unittest.main()
