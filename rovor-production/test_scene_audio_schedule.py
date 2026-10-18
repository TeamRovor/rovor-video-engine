"""Rovor 60fps original-art/acting/score integrated schedule regressions."""
import copy
import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from scene_audio_schedule import prepare
from longform_chapters import plan


def make_art(path, color):
    art=Image.new("RGBA",(128,128),(0,0,0,0))
    ImageDraw.Draw(art).ellipse((8,8,120,120),fill=color)
    art.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acting():
    return {"sourceRig":"original-evan-layered",
            "bodyAction":"Evan catches the animated globe moving across a desk",
            "facialReaction":"Evan follows the object with visible surprise",
            "eyelineTarget":"Center of moving illustrated browser globe",
            "rigControlIds":["right","head","brow_left"]}


def package(root,duration=40):
    n=math.ceil(duration*60-1e-9)
    energy=[(i*.01,-20.) for i in range(math.ceil(duration*100))]
    chapters=plan(duration,energy)
    ids=["evan"]+["prop"+str(i) for i in range(11)]
    assets={}
    for i,key in enumerate(ids):
        fn=key+".png"
        sha=make_art(root/fn,(20+i*18,50+i*12,120+i*10,255))
        assets[key]={"path":fn,"sha256":sha,"kind":"character" if key=="evan" else "prop",
                     "provenance":"rovor-original"}
    kinds=("action","visual-explainer","reaction","object-demo","metaphor")
    shot_count=math.ceil(duration/8)
    shots=[]
    for i in range(shot_count):
        a=i*8
        b=min((i+1)*8,duration)
        kind=kinds[i%len(kinds)]
        sound={"musicMood":"curious"} if i==0 else {"musicMood":"none"}
        if i==0:
            sound["physicalEvents"]=[{
                "atSec":.5,"eventTag":"browser-click",
                "visualAction":"Original Evan visibly taps the computer's browser tab",
                "overDialogue":"quiet-underlay"}]
        shots.append({
            "start":a,"end":b,"kind":kind,
            "visualPurpose":"Original character explains a browser icon through an illustrated scene",
            "animatedActions":["Evan acts with timed arm gestures and props"],
            "composition":"Staged perspective with parallax layers",
            "originalAssetIds":["evan","prop"+str(i%11)],
            "cameraMotion":{"mode":"pan"},
            "actorPerformance":acting() if kind in ("action","reaction","object-demo","metaphor") else None,
            "soundDirection":sound})
    storyboard={"durationSec":duration,"shots":shots}
    catalog={"schemaVersion":1,"approvedForAutomatedPublishing":False,"assets":[
        {"assetId":"sound-effect-real-fixture","category":"sound-effect",
         "ownerConfirmedRights":True,"durationSeconds":.35,
         "eventTags":["browser-click"],"mood":"subtle"},
        {"assetId":"background-music-real-fixture","category":"background-music",
         "ownerConfirmedRights":True,"durationSeconds":60.,
         "eventTags":["curious"],"mood":"curious","vocalContent":"instrumental"},
    ]}
    analysis={"eligibleForProduction":True,"durationSec":duration,
              "audioSha256":"a"*64}
    return [chapters,storyboard,{"schemaVersion":1,"assets":assets},root,catalog,analysis]


class IntegratedSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.args=package(self.folder)
    def tearDown(self):
        self.tmp.cleanup()
    def run_gate(self):
        return prepare(*self.args)
    def test_40s_actual_frames_and_matching_sound(self):
        r=self.run_gate()
        self.assertEqual(r["totalFrames"],2400)
        self.assertEqual(sum(x["expectedFrames"] for x in r["chapters"]),2400)
        self.assertEqual(len(r["soundCues"]["effectCues"]),1)
        self.assertEqual(r["soundCues"]["effectCues"][0]["timeFrame"],30)
        self.assertFalse(r["framesRendered"])
        self.assertFalse(r["creativeApproved"])
    def test_does_not_accept_fake_art(self):
        self.args[2]["assets"]["prop0"]["sha256"]="b"*64
        with self.assertRaises(ValueError):self.run_gate()
    def test_no_substitute_character_rig(self):
        self.args[1]["shots"][0]["actorPerformance"]["sourceRig"]="generated-substitute"
        with self.assertRaises(ValueError):self.run_gate()
    def test_no_undeclared_motion(self):
        self.args[1]["shots"][0]["actorPerformance"].pop("rigControlIds")
        with self.assertRaises(ValueError):self.run_gate()
    def test_fictional_control_name_is_not_real_acting(self):
        self.args[1]["shots"][0]["actorPerformance"]["rigControlIds"]=["evan.eyeline"]
        with self.assertRaises(ValueError):self.run_gate()

    def test_action_cannot_be_head_tilt_only(self):
        self.args[1]["shots"][0]["actorPerformance"]["rigControlIds"]=["head"]
        with self.assertRaises(ValueError):self.run_gate()

    def test_missing_camera_is_not_studio_scene(self):
        self.args[1]["shots"][0].pop("cameraMotion")
        with self.assertRaises(ValueError):self.run_gate()
    def test_rejects_narration_under_30s(self):
        self.args[5]["durationSec"]=22.
        with self.assertRaises(ValueError):self.run_gate()
    def test_no_padded_source_audio(self):
        self.args[0]["chapters"][0]["sourceAudioIsOriginal"]=False
        with self.assertRaises(ValueError):self.run_gate()
    def test_one_unfilled_frame_fails(self):
        self.args[1]["shots"][2]["start"]+=1/60
        with self.assertRaises(ValueError):self.run_gate()
    def test_source_sha_required(self):
        self.args[5]["audioSha256"]="some unrelated 22 second recording"
        with self.assertRaises(ValueError):self.run_gate()
    def test_8m27_has_exact_30473_frames_and_nine_resumable_chapters(self):
        args=package(self.folder,507.8726875)
        result=prepare(*args)
        self.assertEqual(result["totalFrames"],30473)
        self.assertEqual(len(result["chapters"]),9)
        self.assertEqual(result["chapters"][-1]["endFrameExclusive"],30473)
        self.assertEqual(sum(x["expectedFrames"] for x in result["chapters"]),30473)
        self.assertFalse(result["framesRendered"])
        self.assertFalse(result["soundCues"]["mixApproved"])
    def test_sound_must_have_confirmed_rights(self):
        self.args[4]["assets"][0]["ownerConfirmedRights"]=False
        with self.assertRaises(ValueError):self.run_gate()
    def test_source_narration_duration_cannot_drift(self):
        self.args[5]["durationSec"]+=.3
        with self.assertRaises(ValueError):self.run_gate()


if __name__=="__main__":unittest.main()
