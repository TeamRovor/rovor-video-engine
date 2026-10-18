import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256
from PIL import Image,ImageDraw
from layered_art_gate import inspect_art,require_art_ready,PRODUCTION_POSES,REQUIRED_LAYER_TYPES

class TestArtGate(unittest.TestCase):
    def fixture(self,root):
        poses={}
        for i,name in enumerate(PRODUCTION_POSES):
            img=Image.new('RGBA',(720,960),(0,0,0,0))
            d=ImageDraw.Draw(img)
            d.ellipse((80+i*10,130,310+i*9,540),fill=(20+i*20,80,122,255))
            path=root/(name+'.png')
            img.save(path)
            poses[name]={'preview':path.name,'sha256':sha256(path.read_bytes()).hexdigest(), 'layerTypes':list(REQUIRED_LAYER_TYPES)}
        return {
            'kind':'rovor-layered-cartoon-pose-package-v1',
            'style':'original-2d-illustration','characterRole':'secondary-painter',
            'sourceViews':['working-three-quarter'],
            'requiredPoseIds':list(PRODUCTION_POSES),'poses':poses,
            'layouts':{o:{'independentShotComposition':True} for o in ['landscape','portrait']},
            'humanVisualReview':{'artApproved':True,'performanceInMotionApproved':True,
                                 'reviewerEvidence':'Sample signed explicit artist review: fixture only'}
        }
    def test_missing_source_art_fails_closed(self):
        with TemporaryDirectory() as d:
            r=inspect_art({'kind':'rovor-layered-cartoon-pose-package-v1'},d)
            self.assertFalse(r['ready']);self.assertEqual(r['verifiedUniquePoseCount'],0)
            with self.assertRaises(ValueError):require_art_ready({},d)
    def test_complete_synthetic_fixture_proves_rules_not_beauty(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));r=inspect_art(m,d)
            self.assertEqual(r['verifiedUniquePoseCount'],7)
            self.assertTrue(r['ready'])
            self.assertTrue(r['noAutomaticStudioQualityCertification'])
            self.assertFalse(r['publicationApproved'])
    def test_duplicate_pose_file_is_rejected(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));m['poses']['settle']=m['poses']['release']
            self.assertIn('duplicated',str(inspect_art(m,d)['problems']))
    def test_missing_human_approval_is_rejected(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));m['humanVisualReview']['artApproved']=False
            self.assertFalse(inspect_art(m,d)['ready'])
    def test_missing_art_layer_is_rejected(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));m['poses']['high_reach']['layerTypes']=['torso','legs','head']
            self.assertFalse(inspect_art(m,d)['ready'])
    def test_tampered_drawing_fails_checksum(self):
        with TemporaryDirectory() as d:
            r=Path(d);m=self.fixture(r)
            (r/'release.png').write_bytes(b'bad')
            self.assertIn('fingerprint mismatch',str(inspect_art(m,d)['problems']))
    def test_path_escape_denied(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));m['poses']['release']['preview']='../../etc/passwd'
            self.assertIn('missing safe',str(inspect_art(m,d)['problems']))
    def test_portrait_is_not_a_crop_flag(self):
        with TemporaryDirectory() as d:
            m=self.fixture(Path(d));m['layouts']['portrait']['independentShotComposition']=False
            self.assertFalse(inspect_art(m,d)['ready'])

if __name__=='__main__':unittest.main()