"""Real PNG source evidence and deliberately missing cartoon assets regression."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from original_art_story_gate import inspect_storyboard


def make_png(path,color):
    im=Image.new("RGBA",(128,128),(0,0,0,0))
    d=ImageDraw.Draw(im)
    d.ellipse((16,16,112,112),fill=color)
    im.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def storyboard(duration=40):
    kinds=["action","visual-explainer","object-demo","reaction","metaphor"]
    return {"durationSec":duration,"shots":[
        {"start":8*i,"end":8*(i+1),"kind":kind,
         "visualPurpose":"Object performs a distinct action during the narration",
         "animatedActions":["timed original character reaction","prop movement"],
         "originalAssetIds":["evan","browser"],
         "composition":"Moving staged tabletop composition"}
        for i,kind in enumerate(kinds)]}

class PhysicalArtGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.character=self.root/"evan.png"
        self.prop=self.root/"browser.png"
        a=make_png(self.character,"#4c7698")
        b=make_png(self.prop,"#d3a855")
        self.registry={"schemaVersion":1,"assets":{
            "evan":{"kind":"character","path":"evan.png","sha256":a,"provenance":"rovor-original"},
            "browser":{"kind":"prop","path":"browser.png","sha256":b,"provenance":"rovor-original"}
        }}
        self.plan=storyboard()
    def tearDown(self):
        self.tmp.cleanup()
    def check(self):
        return inspect_storyboard(self.plan,self.registry,self.root)
    def test_real_registered_pngs_are_not_artistic_approval(self):
        result=self.check()
        self.assertTrue(result["valid"],result["problems"])
        self.assertTrue(result["artworkIntegrityChecked"])
        self.assertFalse(result["actualMotionInspected"])
        self.assertFalse(result["publicationApproved"])
        self.assertFalse(result["phonemeTimingVerified"])
    def test_fabricated_asset_id_fails(self):
        self.plan["shots"][0]["originalAssetIds"]=["evan","nonexistent-unpainted"]
        report=self.check()
        self.assertFalse(report["valid"])
        self.assertIn("Unregistered source artwork",str(report["problems"]))
    def test_missing_existing_art_fails(self):
        self.prop.unlink()
        self.assertFalse(self.check()["valid"])
    def test_changed_source_art_fails(self):
        make_png(self.prop,"#FF0000")
        self.assertFalse(self.check()["valid"])
    def test_copying_same_png_for_many_fake_assets_fails(self):
        self.registry["assets"]["browser"]["path"]="evan.png"
        self.registry["assets"]["browser"]["sha256"]=self.registry["assets"]["evan"]["sha256"]
        self.assertFalse(self.check()["valid"])
    def test_missing_actual_prop_fails(self):
        self.plan["shots"][0]["originalAssetIds"]=["evan"]
        result=self.check()
        self.assertFalse(result["valid"])
        self.assertIn("no registered illustrated prop",str(result["problems"]))
    def test_unlicensed_or_stock_claim_fails(self):
        self.registry["assets"]["browser"]["provenance"]="stock-video"
        self.assertFalse(self.check()["valid"])
    def test_traversal_rejected(self):
        self.registry["assets"]["browser"]["path"]="../browser.png"
        self.assertFalse(self.check()["valid"])
    def test_short_rejected_even_if_art_exists(self):
        self.plan["durationSec"]=29.9
        self.assertFalse(self.check()["valid"])
    def test_fake_header_not_accepted(self):
        self.prop.write_bytes(b"\x89PNG\r\n\x1a\n"+"".join("X" for _ in range(100)).encode())
        self.registry["assets"]["browser"]["sha256"]=hashlib.sha256(self.prop.read_bytes()).hexdigest()
        self.assertFalse(self.check()["valid"])

if __name__=="__main__":unittest.main()
