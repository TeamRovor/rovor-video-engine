"""Skin isolation and derived matte reconstruction, not animation approval."""
import unittest,json
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from build_construction_skin import split_paint,working_skin_patch
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
class ConstructionSkinTests(unittest.TestCase):
    def test_patch_preserves_alpha_nose_and_outside(self):
        original=np.array(Image.open(ROOT/'oral-rig/face-skin.png').convert('RGBA'));clean=np.array(Image.open(ROOT/'construction-skin-v1/Seal-skin.png').convert('RGBA'));before=original.copy();working,mask,offset=working_skin_patch(original,clean);np.testing.assert_array_equal(original,before);np.testing.assert_array_equal(working[:,:,3],original[:,:,3]);np.testing.assert_array_equal(working[mask==0],original[mask==0]);np.testing.assert_array_equal(working[:311],original[:311]);self.assertTrue(np.isfinite(offset).all())
    def test_derived_paint_reconstructs_each_explicit_roi(self):
        folder=ROOT/'construction-skin-v1';meta=json.loads((folder/'manifest.json').read_text())
        for pose in meta['poses']:
            name=pose['pose'];source=np.array(Image.open(folder/f'references/{name}.png').convert('RGBA'));skin=np.array(Image.open(folder/f'{name}-skin.png').convert('RGBA'));paint,error=split_paint(source,skin,pose['paintROI']);self.assertLess(error,.3);x0,y0,x1,y1=pose['paintROI'];outside=np.ones((512,512),bool);outside[y0:y1,x0:x1]=False;self.assertEqual(int(paint[:,:,3][outside].max()),0)
    def test_optional_profile_changes_only_skin_source(self):
        cv2.setNumThreads(1);old=RoundedDurationCartoonHead();new=ConstructionSkinCartoonHead()
        for name in old.layers:
            if name!='face-skin':np.testing.assert_array_equal(old.layers[name],new.layers[name])
        np.testing.assert_array_equal(old.points['X'],new.points['X']);self.assertEqual(old.geometry,new.geometry)
if __name__=='__main__':unittest.main()
