import copy,json,unittest
import numpy as np
from PIL import Image
from cartoon_torso_bend import TorsoBend,bend_layers,skeptical_bend,PIVOT,CHEST
from painted_character import rotation
from cartoon_body import ROOT

class TorsoBendTests(unittest.TestCase):
    def setUp(self):
        self.im=Image.new('RGBA',(1464,1536));self.im.alpha_composite(Image.open(ROOT/'neck-art-rig/torso.png').convert('RGBA'),(220,0))
        self.rig=TorsoBend(self.im)
    def test_geometry_and_attachment(self):
        v=self.rig.vertices
        for angle in np.linspace(-3,3,241):
            target=self.rig.posed_vertices(float(angle));parent=(np.c_[v,np.ones(len(v))]@rotation(PIVOT,float(angle)).T)[:,:2]
            np.testing.assert_allclose(target[v[:,1]<=CHEST],parent[v[:,1]<=CHEST],atol=1e-4)
            np.testing.assert_array_equal(target[v[:,1]>=PIVOT[1]],v[v[:,1]>=PIVOT[1]])
            self.assertGreater(self.rig.minimum_area2,0)
        for angle in [-4,4,float('nan')]:
            with self.assertRaises(ValueError):self.rig.posed_vertices(angle)
    def test_rest_and_fixed_lower_body(self):
        layers={'torso':self.im,'head':Image.new('RGBA',self.im.size)}
        for k,v in bend_layers(layers,self.rig,0).items():np.testing.assert_array_equal(v,layers[k])
        for angle in [-3,3]:np.testing.assert_array_equal(np.asarray(self.rig.bend(angle))[730:],np.asarray(self.im)[730:])
    def test_cue_shift_and_offcue(self):
        plan={'words':[dict(word=w,start=5+i*.25,end=5.2+i*.25,scriptIndex=i)for i,w in enumerate("that's not some random browser thing".split())]};before=copy.deepcopy(plan)
        self.assertEqual(skeptical_bend(0,plan),0);self.assertEqual(skeptical_bend(8,plan),0)
        self.assertEqual(skeptical_bend(6,plan),-3)
        shifted=copy.deepcopy(plan)
        for w in shifted['words']:w['start']+=2;w['end']+=2
        for t in np.linspace(4,9,121):self.assertAlmostEqual(skeptical_bend(t,plan),skeptical_bend(t+2,shifted))
        self.assertEqual(plan,before);self.assertEqual(skeptical_bend(6,{}),0)
        with self.assertRaises(ValueError):skeptical_bend(float('nan'),plan)

if __name__=='__main__':unittest.main()
