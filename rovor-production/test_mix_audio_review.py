"""Real streaming 32-second stereo mix audition regression, never published."""
import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from audio_library import scan,sha256
from generate_original_music import build
from generate_original_sfx import produce
from soundtrack_editor import propose
from mix_audio_review import mix_review,_gain,_prepare,RATE


class MixReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        produce(cls.root)
        build(cls.root,bars=1)
        cls.catalog=scan(cls.root)
        cls.voice=cls.root/"32-sec-original-test-narration.wav"
        t=np.arange(RATE*32,dtype=np.float32)/RATE
        # Original synthesized voice proxy: none of Evan's private narration.
        y=np.rint(.13*np.sin(2*np.pi*217*t)*32767).astype("<i2")
        with wave.open(str(cls.voice),"wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(RATE)
            f.writeframes(y.tobytes())
        cls.source_hash=sha256(cls.voice)
        cls.story={
            "durationSec":32,
            "shots":[
                {"start":0,"end":2,
                 "soundDirection":{
                   "musicMood":"curious",
                   "physicalEvents":[{
                     "atSec":.5,"eventTag":"browser-click",
                     "visualAction":"Original animated character visibly presses computer tab",
                     "overDialogue":"quiet-underlay"}]}},
                {"start":2,"end":32,"soundDirection":{"intentionalSilence":True}}
            ]
        }
        cls.cues=cls.root/"cue-sheet.json"
        cls.cues.write_text(json.dumps(propose(cls.story,cls.catalog)))
        path=Path.home()/"Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/media-tools/ffmpeg"
        if not path.is_file():
            raise unittest.SkipTest("Known local Mac FFmpeg not installed")
        cls.ffmpeg=path

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_narration_stays_unmodified_in_32_second_review(self):
        dest=self.root/"mix-one.wav"
        result=mix_review(self.voice,self.cues,dest,root=self.root,ffmpeg=self.ffmpeg)
        self.assertAlmostEqual(result["durationSeconds"],32,places=3)
        self.assertEqual(result["samplesPerChannel"],RATE*32)
        self.assertEqual(result["effectCount"],1)
        self.assertEqual(result["musicBedCount"],1)
        self.assertTrue(result["narrationSourceUnchanged"])
        self.assertEqual(result["sourceNarrationSha256"],self.source_hash)
        self.assertEqual(sha256(self.voice),self.source_hash)
        self.assertFalse(result["publicationApproved"])
        self.assertFalse(result["creativeMixApproved"])
        self.assertTrue(dest.with_suffix(".mix-review.json").is_file())
        with wave.open(str(dest),"rb") as f:
            self.assertEqual(f.getframerate(),RATE)
            self.assertEqual(f.getnchannels(),2)
            self.assertEqual(f.getnframes(),RATE*32)
        self.assertNotEqual(sha256(dest),self.source_hash)
        # At 29 sec after intentionally silent underscore, the voice is still
        # the only source in the candidate mix (up to PCM rounding).
        with wave.open(str(dest),"rb") as f:
            f.setpos(29*RATE)
            raw=f.readframes(1024)
        result_audio=np.frombuffer(raw,dtype="<i2").reshape(-1,2)
        with wave.open(str(self.voice),"rb") as f:
            f.setpos(29*RATE)
            voice=np.frombuffer(f.readframes(1024),dtype="<i2")
        self.assertTrue(np.max(np.abs(result_audio[:,0].astype(int)-voice.astype(int)))<=1)

    def test_preview_cannot_overwrite_existing_audio(self):
        dest=self.root/"mix-one.wav"
        if not dest.exists():
            dest.write_bytes(b"some owner's pre-existing export")
        with self.assertRaises(FileExistsError):
            mix_review(self.voice,self.cues,dest,root=self.root,ffmpeg=self.ffmpeg)

    def test_looping_long_music_without_audition_rejected(self):
        data=json.loads(self.cues.read_text())
        data["musicBeds"][0]["endFrameExclusive"]=31*60
        decoded={data["musicBeds"][0]["assetId"]:np.zeros((RATE*2,2),dtype=np.float32),
                 data["effectCues"][0]["assetId"]:np.zeros((RATE//2,2),dtype=np.float32)}
        with self.assertRaises(ValueError):_prepare(data,decoded)

    def test_gain_limits_reject_loud_cues(self):
        for gain in (-3,0,10,-75):
            with self.assertRaises(ValueError):
                _gain({"type":"background-music","gainDbProposal":gain},"background-music")

    def test_nonexistent_asset_cannot_be_mixed(self):
        data=json.loads(self.cues.read_text())
        data["effectCues"][0]["assetId"]="sound-effect-fake"
        bad=self.root/"bad-cues.json"
        bad.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            mix_review(self.voice,bad,self.root/"bad-mix.wav",root=self.root,ffmpeg=self.ffmpeg)
        self.assertFalse((self.root/"bad-mix.wav").exists())

    def test_narration_below_thirty_seconds_rejected(self):
        data=json.loads(self.cues.read_text())
        data["sourceNarrationSeconds"]=22
        bad=self.root/"short-cues.json"
        bad.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            mix_review(self.voice,bad,self.root/"short.wav",root=self.root,ffmpeg=self.ffmpeg)


if __name__=="__main__":
    unittest.main()
