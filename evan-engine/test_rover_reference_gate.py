import copy,hashlib,tempfile,unittest
from pathlib import Path
from PIL import Image
from rover_reference_gate import inspect_references

class RoverReferenceTests(unittest.TestCase):
    def test_sha_verified_and_not_a_production_3d_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=[]
            for name,view in [('board.png','rovor-left-right-and-top'),('side.png','rovor-side-hero')]:
                p=root/name;Image.new('RGBA',(80,60),(255,255,255,255)).save(p)
                rows.append({'id':view,'filename':name,'pixels':[80,60],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            manifest={'schemaVersion':1,'assetCategory':'rovor-autonomous-rover','references':rows}
            r=inspect_references(manifest,root)
            self.assertFalse(r['cartoonRigReady'])
            self.assertFalse(r['productionAssetApproved'])
            wrong=copy.deepcopy(manifest);wrong['references'][0]['sha256']='0'*64
            with self.assertRaises(ValueError):inspect_references(wrong,root)
            wrong=copy.deepcopy(manifest);wrong['references'][0]['filename']='../board.png'
            with self.assertRaises(ValueError):inspect_references(wrong,root)

if __name__=='__main__':unittest.main()