"""Attachment/range safeguards for the word-anchored scene, not art approval."""
import unittest
import numpy as np
from cartoon_index import IndexRig
from cartoon_scene import scene_controls,scene_events
from painted_character import skin_vertices
from cartoon_gesture_body import CartoonRoundedBody

PLAN=dict(words=[dict(word='tiny',start=2.1,end=2.65),dict(word='globe',start=2.92,end=3.27),dict(word='here',start=3.73,end=3.91),dict(word='logo',start=4.36,end=4.83),dict(word='favicon',start=8.51,end=9.15)])

def areas(v,ids):
    tri=v[ids];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0];return a[:,0]*b[:,1]-a[:,1]*b[:,0]

class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rig=IndexRig();cls.body=CartoonRoundedBody()
    def test_index_mesh_preserves_orientation_through_scene(self):
        ids=np.array(self.rig.triangles);rest=areas(self.rig.vertices,ids)
        for i in range(489):
            posed=self.rig.posed_vertices(scene_controls(i/48,PLAN)['index'])
            self.assertGreater(float(np.min(areas(posed,ids)/rest)),.01)
    def test_finger_joints_share_parent_transform(self):
        for angles in [(-10,60,35),(-5,30,18),(0,0,0)]:
            a,b,c=self.rig.matrices(angles)
            np.testing.assert_allclose(a@np.r_[self.rig.joints[1],1],b@np.r_[self.rig.joints[1],1],atol=.001)
            np.testing.assert_allclose(b@np.r_[self.rig.joints[2],1],c@np.r_[self.rig.joints[2],1],atol=.001)
    def test_authored_arm_range_has_no_foldovers(self):
        for i in range(489):
            controls=scene_controls(i/48,PLAN)
            for name,arm in self.body.arms.items():
                v=skin_vertices(arm.vertices,arm.geometry,controls[name]);tri=v[np.array(arm.triangles)];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),1)
    def test_point_is_held_on_anchors_and_released_in_pause(self):
        self.assertEqual(len(scene_events(PLAN)),2)
        for t in (3.2,3.8,8.8,9.1):np.testing.assert_allclose(scene_controls(t,PLAN)['index'],[0,0,0],atol=.001)
        self.assertGreater(scene_controls(9.9,PLAN)['index'][1],40)
        np.testing.assert_allclose(scene_controls(10.18,PLAN)['right'],[-2,0,0],atol=.01)
    def test_absent_cues_leave_safe_idle_pose(self):
        p=dict(words=[]);self.assertEqual(scene_events(p),[])
        np.testing.assert_allclose(scene_controls(2,p)['right'],[-2,0,0])

    def test_unreviewed_fold_range_is_rejected(self):
        with self.assertRaises(ValueError):self.rig.posed_vertices([-30,95,70])

if __name__=='__main__':unittest.main()
