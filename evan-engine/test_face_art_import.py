"""Prevent blank templates and reference composites entering the art handoff."""
import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from psd_tools import PSDImage
from face_art_contract import PLANES,SIZE
from audit_face_art_psd import audit

class FaceArtImportTests(unittest.TestCase):
    def make(self,path,paint=False,flat=False,opacity=False,missing_teeth=False):
        psd=PSDImage.frompil(Image.new('RGBA',SIZE))
        # Visible references must never contaminate exported component pixels.
        ref=psd.create_pixel_layer(Image.new('RGBA',SIZE,'#f9a36e'),name='REFERENCE__context');ref.visible=True
        psd.create_pixel_layer(Image.new('RGBA',SIZE,'#00ff00'),name='GUIDE__registration')
        for name,(x,y,_,_) in PLANES.items():
            im=Image.new('RGBA',SIZE)
            if paint and not (missing_teeth and name=='upper-teeth'):
                d=ImageDraw.Draw(im);d.rectangle((x+4,y+4,x+12,y+12),fill=(180,90,70,199))
            if flat and name=='jaw-skin':im=Image.new('RGBA',SIZE,(180,90,70,255))
            layer=psd.create_pixel_layer(im,name='ART__'+name)
            if opacity and name=='jaw-skin':layer.opacity=128
        psd.save(path)
    def test_blank_templates_rejected_without_partial_export(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);self.make(p/'blank.psd');r=audit(p/'blank.psd','Release',p/'staging')
            self.assertFalse(r['structuralPass']);self.assertFalse((p/'staging').exists());self.assertTrue(any('required paint' in i for i in r['issues']))
    def test_labiodental_requires_teeth_but_bilabial_contact_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'without-teeth.psd';self.make(p,True,missing_teeth=True)
            self.assertTrue(audit(p,'Contact')['structuralPass'])
            for pose in ['Labiodental','LabiodentalRelease']:
                r=audit(p,pose);self.assertFalse(r['structuralPass']);self.assertTrue(any('upper-teeth: required paint' in i for i in r['issues']))
    def test_labiodental_release_keeps_incisor_and_upper_lip_anchors(self):
        from face_art_contract import POSES
        from build_face_drawing_templates import guides
        a=POSES['Labiodental'];b=POSES['LabiodentalRelease']
        self.assertEqual(a['upper'],b['upper']);self.assertEqual(a['toothTips'],b['toothTips']);self.assertGreater(b['lower'][1],a['lower'][1]);self.assertEqual(a['lower'][1],a['toothTips'][0][1])
        _,anchors=guides('Labiodental');self.assertEqual(anchors['incisorLeftTip'],a['toothTips'][0]);self.assertEqual(anchors['leftCorner'],a['corners']['left'])
    def test_flattened_head_and_group_opacity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);self.make(p/'flat.psd',True,flat=True);r=audit(p/'flat.psd','Open');self.assertFalse(r['structuralPass']);self.assertTrue(any('outside drawing envelope' in i for i in r['issues']))
            self.make(p/'opacity.psd',True,opacity=True);r=audit(p/'opacity.psd','Open');self.assertFalse(r['structuralPass']);self.assertTrue(any('full layer opacity' in i for i in r['issues']))
    def test_export_is_exact_separated_paint_not_reference_or_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);self.make(p/'parts.psd',True);r=audit(p/'parts.psd','Open',p/'staging')
            self.assertTrue(r['structuralPass']);self.assertFalse(r['animationReady']);self.assertFalse(r['runtimeLoaded']);self.assertEqual(len(r['exported']),len(PLANES))
            self.assertEqual(len(r['ignoredReferenceAndGuideLayers']),2)
            opened=PSDImage.open(p/'parts.psd')
            for l in opened:
                if l.name.startswith('ART__'):np.testing.assert_array_equal(np.array(l.topil().convert('RGBA')),np.array(Image.open(p/'staging'/(l.name[5:]+'.png'))))
if __name__=='__main__':unittest.main()
