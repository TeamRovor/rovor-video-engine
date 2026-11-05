"""Bounded per-head inverse-mesh cache. No rendered images or frames are cached."""
from collections import OrderedDict
from cartoon_head import warp_maps,sample_warp
class CachedSurfaceMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._surface_cache=OrderedDict();self.mesh_cache_hits=0;self.mesh_cache_misses=0
    def sample_surface(self,image,source,target,sample_scale=1):
        key=(source.dtype.str,source.shape,source.tobytes(),target.dtype.str,target.shape,target.tobytes(),sample_scale)
        if key in self._surface_cache:
            self.mesh_cache_hits+=1;fields=self._surface_cache.pop(key)
        else:
            self.mesh_cache_misses+=1;fields=warp_maps(source,target,sample_scale)
        self._surface_cache[key]=fields
        while len(self._surface_cache)>4:self._surface_cache.popitem(last=False)
        # Dynamic image pixels and constrained premultiplication are sampled
        # anew on every call, including tongue deformation. Keys include ALL
        # source/target points and sample scale, not frame/viseme identity.
        return self.constrain_surface(sample_warp(image,fields,sample_scale))
