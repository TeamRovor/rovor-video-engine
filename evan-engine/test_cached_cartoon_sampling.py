"""Mesh-field cache equivalence/invalidation; rendered pixels never cached."""
import unittest
import cv2,numpy as np
from duration_cartoon_head import DurationCartoonHead
from cached_cartoon_sampling import CachedSurfaceMixin
from cartoon_head import POINTS
class CachedDuration(CachedSurfaceMixin,DurationCartoonHead):pass
class CacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.old=DurationCartoonHead();cls.new=CachedDuration()
    def test_dynamic_images_share_geometry_not_pixels(self):
        target=POINTS['C'].copy();before=self.new.mesh_cache_hits;results=[]
        for image in [self.new.blade,self.new.root_floor]:
            a=self.old.sample_surface(image,POINTS['H'],target,2);b=self.new.sample_surface(image,POINTS['H'],target,2);np.testing.assert_array_equal(a,b);results.append(b)
        self.assertGreater(self.new.mesh_cache_hits,before);self.assertFalse(np.array_equal(*results))
    def test_points_scale_and_eviction_invalidate_fields(self):
        image=self.new.layers['upper-teeth'];source=POINTS['C'].copy()
        for i in range(7):
            target=POINTS['D'].copy();target[:32,1]+=i*.125;scale=1+i%2
            np.testing.assert_array_equal(self.old.sample_surface(image,source,target,scale),self.new.sample_surface(image,source,target,scale))
            self.assertLessEqual(len(self.new._surface_cache),4)
    def test_full_control_images_exact_with_cache(self):
        for i in [0,3,5,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
if __name__=='__main__':unittest.main()
