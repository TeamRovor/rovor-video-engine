"""Cinematic original-layer 2D direction tests at 60fps, both views."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from directed_scene import check,DirectedScene


def art(path,color):
    im=Image.new("RGBA",(140,140),(0,0,0,0))
    ImageDraw.Draw(im).rounded_rectangle((20,20,120,120),radius=18,fill=color)
    im.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(frame,x=.5,y=.5,scale=.55,rotation=0.,opacity=1.):
    return {"frame":frame,"x":x,"y":y,"scale":scale,
            "rotation":rotation,"opacity":opacity}


def camera(frame,pan=0.,zoom=1.):
    return {"frame":frame,"panX":pan,"panY":0.,"zoom":zoom}


def fixture(root):
    registry={"schemaVersion":1,"assets":{}}
    for name,color in (("desk","#866b52"),("globe","#3c9ba1")):
        filename=name+".png"
        registry["assets"][name]={"path":filename,"sha256":art(root/filename,color),
                                  "kind":"prop","provenance":"rovor-original"}
    shots=[]
    for index,kind in enumerate(("action","reaction","object-demo","visual-explainer","metaphor")):
        begin=index*480
        end=begin+480
        comps={}
        for vertical in ("portrait","landscape"):
            dy=.22 if vertical=="portrait" else .0
            comps[vertical]={
                "background":"#f3f0e8",
                "camera":[camera(begin,0,1.0),camera(end,.035 if index%2 else -.035,1.08)],
                "elements":[
                    {"assetId":"desk","role":"background",
                     "keys":[key(begin,.5,.78+dy,.7),key(end,.5,.78+dy,.7)]},
                    {"assetId":"original-evan-rig","role":"character",
                     "keys":[key(begin,.64,.55+dy,.60),key(end,.64,.55+dy,.60)]},
                    {"assetId":"globe","role":"prop",
                     "keys":[key(begin,.17,.6+dy,.5),key(end,.55,.6+dy,.5,10.)]},
                ],
            }
        shots.append({"kind":kind,"startFrame":begin,"endFrameExclusive":end,
            "visualPurpose":"An original character observes a moving illustration and reacts",
            "actionPayoff":"The animated globe reaches the foreground object",
            "compositions":comps})
    return {"schemaVersion":1,"durationSec":40,"shots":shots},registry


class DirectedSceneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.config,self.registry=fixture(self.root)
        self.evan=Image.new("RGBA",(280,360),(0,0,0,0))
        ImageDraw.Draw(self.evan).ellipse((75,5,205,180),fill="#1d3145")
    def tearDown(self):
        self.temp.cleanup()
    def test_both_viewpoints_and_real_motion(self):
        result=check(self.config,self.registry,self.root)
        self.assertEqual(result["totalFrames"],2400)
        self.assertFalse(result["creativeApproved"])
        for portrait,size in ((False,(1920,1080)),(True,(1080,1920))):
            scene=DirectedScene(self.config,self.registry,self.root,portrait)
            before=scene.frame(0,self.evan)
            after=scene.frame(200,self.evan)
            self.assertEqual(before.size,size)
            self.assertEqual(after.size,size)
            x=np.asarray(before).astype(np.int16)
            y=np.asarray(after).astype(np.int16)
            self.assertGreater(np.mean(np.abs(x-y)),.35)
    def test_missing_original_assets_fail_closed(self):
        self.registry["assets"]["globe"]["sha256"]="0"*64
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_no_generic_single_view_reframing(self):
        del self.config["shots"][0]["compositions"]["portrait"]
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_extended_static_talking_scene_rejected(self):
        self.config["shots"][0]["endFrameExclusive"]=700
        self.config["shots"][0]["compositions"]["landscape"]["elements"][-1]["keys"][-1]["x"]=.17
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_short_under_30s_rejected(self):
        self.config["durationSec"]=22
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_scene_gap_rejected(self):
        self.config["shots"][1]["startFrame"]+=1
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_no_fake_source_replacement(self):
        self.registry["assets"]["globe"]["provenance"]="stock"
        with self.assertRaises(ValueError):check(self.config,self.registry,self.root)
    def test_missing_actor_frame_must_fail(self):
        scene=DirectedScene(self.config,self.registry,self.root,False)
        with self.assertRaises(ValueError):scene.frame(1,None)
    def test_camera_and_prop_content_are_distinct(self):
        s=DirectedScene(self.config,self.registry,self.root,False)
        first=np.asarray(s.frame(0,self.evan))
        second=np.asarray(s.frame(450,self.evan))
        self.assertGreater(np.mean(np.abs(first.astype(float)-second.astype(float))),.4)
    def test_all_scene_transitions_have_valid_synchronized_frames(self):
        scene=DirectedScene(self.config,self.registry,self.root,False)
        for f in (0,479,480,959,960,1439,1440,1919,1920,2399):
            self.assertEqual(scene.frame(f,self.evan).size,(1920,1080))
        with self.assertRaises(ValueError):scene.frame(2400,self.evan)


if __name__=="__main__":unittest.main()
