"""Continuous-skin safeguards; not anatomical or animation acceptance."""
import unittest,json
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from compact_cartoon_scene import CompactCartoonSceneBody,compact_controls
from joined_cartoon_wrist import JoinedWristSceneBody
from painted_character import skin_vertices,arm_transforms
from test_cartoon_scene import PLAN,areas
class JoinedWristTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=CompactCartoonSceneBody();cls.new=JoinedWristSceneBody()
    def test_all_scene_frames_keep_arm_orientation(self):
        arm=self.new.arms['right'];ids=np.array(arm.triangles)
        for i in range(489):
            c=compact_controls(i/48,PLAN);v=skin_vertices(arm.vertices,arm.geometry,c['right'])
            self.assertGreater(float(areas(v,ids).min()),1.)
    def test_original_forearm_grid_retained(self):
        old=self.old.arms['right'].vertices;new=self.new.arms['right'].vertices
        self.assertTrue(set(map(tuple,old)).issubset(set(map(tuple,new))))
    def test_distal_skin_uses_index_parent_transform(self):
        arm=self.new.arms['right'];distal=arm.vertices[:,1]>=arm.geometry['wrist'][1]+30;v=arm.vertices[distal]
        for t in [0,8.8,9.65,10.16]:
            c=compact_controls(t,PLAN);expected=(np.c_[v,np.ones(len(v))]@arm_transforms(arm.geometry,c['right'])[2].T)[:,:2]
            np.testing.assert_allclose(skin_vertices(v,arm.geometry,c['right']),expected,atol=.001)
    def test_remote_source_pixels_and_distal_palm_preserved(self):
        original=np.asarray(Image.open(ROOT/'body-rig/arm-right.png').convert('RGBA'));palm=np.asarray(Image.open(ROOT/'index-rig/palm.png').convert('RGBA'));joined=np.asarray(Image.open(ROOT/'wrist-rig/right-skin.png').convert('RGBA'))
        yy,xx=np.mgrid[:1536,:1024];axis=np.array([61.,137.]);axis/=np.linalg.norm(axis);s=(xx-810)*axis[0]+(yy-762)*axis[1]
        np.testing.assert_array_equal(original[s<=-36],joined[s<=-36]);np.testing.assert_array_equal(palm[s>=40],joined[s>=40])
    def test_wrist_interior_opaque(self):
        import cv2
        im=np.asarray(Image.open(ROOT/'wrist-rig/right-skin.png').convert('RGBA'));axis=np.array([61.,137.]);axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]]);s=np.linspace(-36,24,121);q=np.linspace(-8,8,33);xy=np.array([810.,762.])+s[:,None,None]*axis+q[None,:,None]*normal
        alpha=cv2.remap(im[:,:,3],xy[:,:,0].astype('float32'),xy[:,:,1].astype('float32'),cv2.INTER_LINEAR)
        self.assertGreaterEqual(int(alpha.min()),250)

    def test_retained_mesh_covers_all_source_skin(self):
        import cv2
        arm=self.new.arms['right'];coverage=np.zeros(arm.image.shape[:2],np.uint8)
        for ids in arm.triangles:cv2.fillConvexPoly(coverage,np.rint(arm.vertices[list(ids)]).astype('int32'),255)
        self.assertTrue(np.all(coverage[arm.image[:,:,3]>0]>0))
