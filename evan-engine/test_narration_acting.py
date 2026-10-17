import unittest
import numpy as np
from cartoon_body import CartoonBody, narration_acting
from cartoon_expression import eyebrow_maps
from painted_character import arm_transforms, skin_vertices


class NarrationActingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.body=CartoonBody()

    def test_full_take_has_safe_meshes_and_attached_pointing_wrist(self):
        body=self.body
        for t in np.arange(1323)/60:
            controls=narration_acting(float(t))
            arms=list(body.arms.items())
            if controls['right_hand']=='point':arms.append(('right',body.point_forearm))
            for name,arm in arms:
                v=skin_vertices(arm.vertices,arm.geometry,controls[name])
                tri=v[np.asarray(arm.triangles)]
                a,b=tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),0)
            plate=body.point_hand
            actual=plate.transform(controls['right']) @ plate.anchor
            attachment=plate.base @ plate.anchor
            expected=arm_transforms(plate.geometry,controls['right'])[2] @ attachment
            np.testing.assert_allclose(actual,expected,atol=.001)
            corners=plate.corners @ plate.transform(controls['right']).T
            self.assertGreater(float(corners[:,0].min()+220),0)
            self.assertLess(float(corners[:,0].max()+220),1464)

    def test_rest_returns_at_end_and_late_acting_exists(self):
        self.assertNotEqual(narration_acting(11)['right'],narration_acting(18)['right'])
        end=narration_acting(22.047375)
        self.assertEqual(end['right'],[0,0,0])

    def test_brow_motion_keeps_glasses_hair_and_mouth_fixed(self):
        yy,xx=np.indices((512,512),dtype='float32')
        for left,right in [(5,-5),(-5,5),(3,3)]:
            mx,my=eyebrow_maps(512,left,right)
            np.testing.assert_array_equal(mx,xx)
            np.testing.assert_array_equal(my[:196],yy[:196])
            np.testing.assert_array_equal(my[234:],yy[234:])
            self.assertGreater(float(np.min(np.diff(my,axis=0))),.2)


if __name__=='__main__':unittest.main()
