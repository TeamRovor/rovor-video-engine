import unittest
try:
 import numpy as np
 from PIL import Image
 from layered_cartoon_head import LayeredCartoonHead,ROOT
 from build_cartoon_heads import key_cartoon_plate
except ImportError:np=None

@unittest.skipIf(np is None,'Optional cartoon dependencies')
class OralLayerTests(unittest.TestCase):
 def test_matte_keeps_teeth_and_ink_not_magenta(self):
  a=np.array([[[255,0,255,255],[255,245,220,255],[12,10,9,255]]],np.uint8)
  result=np.asarray(key_cartoon_plate(Image.fromarray(a)))
  self.assertEqual(result[0,0,3],0);self.assertEqual(result[0,1,3],255);self.assertEqual(result[0,2,3],255)
 def test_closure_hides_teeth_and_tongue(self):
  h=LayeredCartoonHead();a=np.asarray(h.weights(np.eye(9)[1]));roi=a[309:370,180:290]
  self.assertEqual(int(((roi[:,:,0]>180)&(roi[:,:,1]>190)&(roi[:,:,2]>160)).sum()),0)
 def test_upper_face_stays_fixed(self):
  h=LayeredCartoonHead();base=h.images['X']
  for w in (np.eye(9)[3],np.eye(9)[5],np.eye(9)[8]):self.assertTrue(np.array_equal(np.asarray(h.weights(w))[:292],base[:292]))
 def test_rounded_vowel_hides_white_teeth(self):
  h=LayeredCartoonHead();a=np.asarray(h.weights(np.eye(9)[5]));roi=a[309:375,180:290]
  self.assertEqual(int(((roi[:,:,0]>180)&(roi[:,:,1]>190)&(roi[:,:,2]>160)).sum()),0)
 def test_layers_are_separate_and_localized(self):
  h=LayeredCartoonHead()
  for name in ('cavity-outline','upper-teeth','tongue','tongue-raised','closed-lips','fv-contact'):
   a=h.layers[name];self.assertEqual(a.shape,(512,512,4));self.assertEqual(a[:300,:,3].max(),0);self.assertGreater(a[:,:,3].max(),0)
 def test_hidden_skin_has_no_remaining_lip_stroke(self):
  h=LayeredCartoonHead();skin=h.layers['face-skin'][309:336,190:288,:3]
  self.assertEqual(int((skin.max(axis=2)<235).sum()),0)
