import unittest
import numpy as np
from PIL import Image
from layered_cartoon_head import LayeredCartoonHead,ROOT
from cartoon_head import POINTS,warp,warp_maps


class MouthAnatomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=LayeredCartoonHead();cls.new=LayeredCartoonHead(mouth_anatomy=True)

    def render(self,head,symbol):
        w=np.zeros(9);w['XABCDEFGH'.index(symbol)]=1
        return np.asarray(head.weights(w))

    def test_shared_mapping_preserves_exact_art_pixels(self):
        source=self.old.layers['upper-teeth']
        target=POINTS['C']*.4+POINTS['H']*.6
        direct=warp(source,POINTS['C'],target,2)
        shared=warp(source,POINTS['C'],target,2,maps=warp_maps(POINTS['C'],target,2))
        np.testing.assert_array_equal(direct,shared)

    def test_l_tongue_is_retracted_behind_front_teeth(self):
        before=self.render(self.old,'H')[305:365,180:295,:3]
        after=self.render(self.new,'H')[305:365,180:295,:3]
        red=lambda a:(a[:,:,0]>130)&(a[:,:,1]<130)&(a[:,:,0]>a[:,:,1]*1.5)
        white=lambda a:(a[:,:,0]>180)&(a[:,:,1]>170)&(a[:,:,2]>130)
        self.assertLess(int(red(after).sum()),int(red(before).sum())*.8)
        self.assertGreaterEqual(int(white(after).sum()),int(white(before).sum()))

    def test_contact_art_narrowed_without_changing_other_face_pixels(self):
        old=np.asarray(Image.open(ROOT/'oral-rig/fv-contact.png'))[:,:,3]
        new=np.asarray(Image.open(ROOT/'oral-rig/fv-contact-v3.png'))[:,:,3]
        bounds=lambda a:np.ptp(np.where(a>128)[0])
        self.assertLess(bounds(new),bounds(old))
        a=self.render(self.old,'G');b=self.render(self.new,'G')
        np.testing.assert_array_equal(a[:300],b[:300])
        np.testing.assert_array_equal(a[350:],b[350:])

    def test_bilabial_closure_remains_identical(self):
        np.testing.assert_array_equal(self.render(self.old,'A'),self.render(self.new,'A'))


if __name__=='__main__':unittest.main()
