"""Narrative cue isolation and hierarchy safeguards, not performance approval."""
import copy,json,unittest,cv2
from pathlib import Path
import numpy as np
from finished_cartoon_scene import finish_event,finished_controls,favicon_progress,favicon_weights,FinishedCartoonHead,FinishedCartoonSceneBody
from detail_cartoon_scene import detail_controls,DetailCartoonHead
class FinishedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
    def test_contiguous_words_and_missing_cues(self):
        self.assertEqual(finish_event(self.plan)['scriptIndices'],list(range(50,56)))
        p=copy.deepcopy(self.plan);p['words'][52]['word']='other';self.assertIsNone(finish_event(p));self.assertEqual(favicon_progress(20,p),0)
    def test_reveal_is_bounded_monotone_at_website(self):
        self.assertEqual(favicon_progress(17.18,self.plan),0)
        self.assertEqual(favicon_progress(17.54,self.plan),1)
        values=[favicon_progress(t,self.plan) for t in np.linspace(0,22,1059)]
        self.assertGreaterEqual(min(values),0);self.assertLessEqual(max(values),1);self.assertGreaterEqual(min(np.diff(values)),0)
    def test_official_mark_never_ghosts_into_globe(self):
        for p in np.linspace(0,1,101):
            old,new=favicon_weights(p);self.assertEqual(old*new,0.)
        self.assertEqual(favicon_weights(0),(1.,0.));self.assertEqual(favicon_weights(1),(0.,1.))
    def test_controls_are_isolated_continuous_plan_unchanged(self):
        before=copy.deepcopy(self.plan)
        for t in [0.,10.,15.5,17.,20.,22.]:self.assertEqual(finished_controls(t,self.plan),detail_controls(t,self.plan))
        rows=[]
        for t in np.arange(17.,19.8,1/480):
            c=finished_controls(float(t),self.plan);rows.append(c['right']+c['left']+[c['head'],c['body_roll']])
        self.assertLess(abs(np.diff(rows,axis=0)).max(),.25);self.assertEqual(before,self.plan)
    def test_brow_isolation(self):
        new=FinishedCartoonHead.__new__(FinishedCartoonHead);old=DetailCartoonHead.__new__(DetailCartoonHead)
        for t in [0.,15.5,17.,20.,22.]:self.assertEqual(new.expression_control(t,self.plan),old.expression_control(t,self.plan))
        self.assertGreater(new.expression_control(18.8,self.plan)['rightRaise'],2.)
    def test_separated_face_keeps_body_layers_and_finished_brow_acting(self):
        cv2.setNumThreads(1);body=FinishedCartoonSceneBody();t=18.5
        before=body.layers(t,self.plan);expression=body.head.expression_control(t,self.plan)
        body.enable_separated_face();head=body.head;body.enable_separated_face();self.assertIs(head,body.head)
        after=body.layers(t,self.plan)
        self.assertEqual(list(before),list(after));self.assertEqual(body.head.expression_control(t,self.plan),expression)
        for name in before:
            if name not in ('head','neck'):np.testing.assert_array_equal(np.array(before[name]),np.array(after[name]))
        self.assertFalse(np.array_equal(np.array(before['head']),np.array(after['head'])))
        self.assertEqual(len(body.head.rig.last_parts),10);self.assertTrue(body.head.last_audit['upper288Exact'])
    def test_arm_meshes_through_reference(self):
        body=FinishedCartoonSceneBody()
        for i in range(1059):
            c=finished_controls(i/48,self.plan)
            for name,arm in body.arms.items():
                tri=arm.posed_vertices(c[name])[np.array(arm.triangles)];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)
if __name__=='__main__':unittest.main()
