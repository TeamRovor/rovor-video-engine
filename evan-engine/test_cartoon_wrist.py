import unittest
import numpy as np
from PIL import Image
from cartoon_body import CartoonBody,narration_acting
from painted_character import arm_transforms


class WristSurfaceTests(unittest.TestCase):
    def test_point_and_breakdown_have_no_transparent_strip_at_joint(self):
        body=CartoonBody()
        for t in (2.25,2.6,4.83):
            controls=narration_acting(t);pose=controls['right_hand']
            plate=body.hand_plates[pose];angles=controls['right']
            canvas=Image.new('RGBA',(1464,1536))
            for part in (body.point_forearm,plate):
                im,(x,y)=part.render(angles);canvas.alpha_composite(im,(x+220,y))
            joint=(plate.transform(angles)@plate.anchor)[:2]+[220,0]
            fore=arm_transforms(plate.geometry,angles)[1]
            elbow=(fore@np.r_[plate.geometry['elbow'],1])[:2]+[220,0]
            axis=joint-elbow;axis/=np.linalg.norm(axis)
            alpha=np.asarray(canvas)[:,:,3]
            for offset in np.linspace(-8,8,33):
                x,y=np.rint(joint+axis*offset).astype(int)
                self.assertGreaterEqual(int(alpha[y,x]),245,(t,offset))


if __name__=='__main__':unittest.main()
