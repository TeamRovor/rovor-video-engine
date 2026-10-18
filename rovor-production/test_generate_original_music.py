"""Regression tests for reproducible unlicensed-sample-free score sketches."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import wave

import numpy as np
from audio_library import scan
from generate_original_music import SCORES, RATE, render_score, build


class MusicTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def test_three_unique_instrumental_timbres(self):
        result=[]
        for name in SCORES:
            mix,duration=render_score(name,bars=1)
            self.assertEqual(mix.shape,(round(duration*RATE),2))
            self.assertGreater(np.max(np.abs(mix)),.05)
            self.assertLess(np.max(np.abs(mix)),.85)
            self.assertTrue(np.isfinite(mix).all())
            self.assertTrue(np.max(np.abs(mix[:250]))<.2)
            self.assertTrue(np.max(np.abs(mix[-250:]))<.2)
            result.append(hashlib.sha256(mix.tobytes()).hexdigest())
        self.assertEqual(len(set(result)),3)
    def test_catalog_registers_music_moods_without_speech(self):
        created=build(self.root,bars=1)
        self.assertEqual(len(created),3)
        catalog=scan(self.root)
        songs=[r for r in catalog["assets"] if r["category"]=="background-music"]
        self.assertEqual(len(songs),3,catalog["rejected"])
        self.assertTrue(all(r["vocalContent"]=="instrumental" for r in songs))
        self.assertEqual({r["mood"] for r in songs},{"curious","playful","inspiring"})
        self.assertFalse(catalog["approvedForAutomatedPublishing"])
        self.assertTrue(all(r["editorialApproved"] is False for r in songs))
    def test_rerun_does_not_overwrite(self):
        build(self.root,bars=1)
        path=self.root/"BackgroundMusic"/"rovor-curious-expedition.wav"
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(build(self.root,bars=1),[])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),h)
    def test_corrupted_or_user_supplied_music_never_overwritten(self):
        folder=self.root/"BackgroundMusic"
        folder.mkdir(parents=True)
        file=folder/"rovor-curious-expedition.wav"
        file.write_bytes(b"Do not overwrite something authored by the owner.")
        with self.assertRaises(ValueError):build(self.root,bars=1)
        self.assertTrue(file.read_bytes().startswith(b"Do not overwrite"))
    def test_generated_music_is_48k_stereo_pcm(self):
        build(self.root,bars=1)
        for key in SCORES:
            path=self.root/"BackgroundMusic"/("rovor-"+key+".wav")
            with wave.open(str(path),"rb") as f:
                self.assertEqual(f.getframerate(),RATE)
                self.assertEqual(f.getnchannels(),2)
                self.assertEqual(f.getsampwidth(),2)
                self.assertGreater(f.getnframes(),SR)
            sidecar=json.loads((path.with_name(path.name+".asset.json")).read_text())
            self.assertEqual(sidecar["sourceSha256"],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(sidecar["automatedPublishingApproved"])
            self.assertEqual(sidecar["listeningReviewStatus"],"NOT_ARTISTICALLY_APPROVED")
    def test_invalid_score_or_illegal_bars_rejected(self):
        for bars in (0,25,True,-1):
            with self.assertRaises(ValueError):render_score("curious-expedition",bars)
        with self.assertRaises(ValueError):render_score("fake-song",1)


if __name__=="__main__":
    unittest.main()
