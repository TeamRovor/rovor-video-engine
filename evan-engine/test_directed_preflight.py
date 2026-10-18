"""Real 40-second source-audio preflight: reject failures without rendering."""
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from speech_planner import audio_envelope
from test_directed_scene import fixture
from test_performance_tracks import authored


class LongformPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        frames=16000*40
        t=np.arange(frames,dtype=np.float32)/16000
        sound=np.rint(0.16*np.sin(2*np.pi*220*t)*32767).clip(-32768,32767).astype("<i2")
        self.audio=self.root/"40sec-source.wav"
        with wave.open(str(self.audio),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(sound.tobytes())
        director,registry=fixture(self.root)
        performance=authored(40)
        cues={
            "status":"EDITORIAL_AUDIO_CUE_PROPOSALS",
            "sourceNarrationSeconds":40,"fps":60,
            "mixApproved":False,"noAutomaticPublishing":True,
            "effectCues":[{"shot":1,"timeFrame":120,
                           "animatedAssetId":"globe","type":"sound-effect"}],
            "musicBeds":[]
        }
        data={"source.json":{"audio":audio_envelope(self.audio)},
              "director.json":director,
              "assets.json":registry,
              "performance.json":performance,
              "cues.json":cues}
        for name,obj in data.items():
            (self.root/name).write_text(json.dumps(obj))
        self.out=self.root/"should-not-create-video"
    def tearDown(self):
        self.tmp.cleanup()
    def command(self):
        return [
            sys.executable,str(Path(__file__).parent/"render_acting_video.py"),
            str(self.root/"source.json"),str(self.audio),str(self.out),
            "--ffmpeg","/not-used-in-preflight",
            "--visual-mode","directed",
            "--director-json",str(self.root/"director.json"),
            "--art-registry",str(self.root/"assets.json"),
            "--performance-json",str(self.root/"performance.json"),
            "--sound-cues",str(self.root/"cues.json"),
            "--preflight-only"
        ]
    def test_valid_video_work_fails_closed_as_not_yet_rendered(self):
        run=subprocess.run(self.command(),capture_output=True,text=True,timeout=75)
        self.assertEqual(run.returncode,0,run.stderr[-2000:])
        self.assertIn("ROVOR_PREFLIGHT_OK_NOT_RENDERED",run.stdout)
        self.assertIn('"framesToRender": 2400',run.stdout)
        self.assertIn("VERIFIED_PHYSICAL_SFX_CUES=1",run.stdout)
        self.assertIn('"bodyFrameDiskCacheEnabled": false',run.stdout)
        self.assertFalse(self.out.exists())
    def test_bad_cue_cannot_trigger_expensive_render(self):
        path=self.root/"cues.json"
        cues=json.loads(path.read_text())
        cues["effectCues"][0]["animatedAssetId"]="not-a-real-object"
        path.write_text(json.dumps(cues))
        run=subprocess.run(self.command(),capture_output=True,text=True,timeout=75)
        self.assertNotEqual(run.returncode,0)
        self.assertFalse(self.out.exists())
    def test_invalid_source_original_voice_evidence_rejected(self):
        path=self.root/"source.json"
        data=json.loads(path.read_text())
        data["audio"]["rms"][0]+=.08
        path.write_text(json.dumps(data))
        run=subprocess.run(self.command(),capture_output=True,text=True,timeout=75)
        self.assertNotEqual(run.returncode,0)
        self.assertFalse(self.out.exists())


if __name__=="__main__":
    unittest.main()
