"""Two-format review promotion must not replace accepted video on one failure."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from promote_verified_pair import promote
from test_verify_longform_export import write_wav


class SafePromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg=os.environ.get("ROVOR_TEST_FFMPEG","")
        if not cls.ffmpeg or not Path(cls.ffmpeg).is_file():
            raise unittest.SkipTest("Mac FFmpeg explicitly configured for tests")
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.wav=cls.root/"40second-source.wav"
        cls.media=cls.root/"full-source.mp4"
        write_wav(cls.wav,31.2)
        cls.sha=hashlib.sha256(cls.wav.read_bytes()).hexdigest()
        subprocess.run([
            cls.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y",
            "-f","lavfi","-i","color=c=black:s=320x180:r=60:d=31.2",
            "-i",str(cls.wav),"-map","0:v:0","-map","1:a:0",
            "-c:v","libx264","-preset","ultrafast","-crf","35",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest",
            str(cls.media)],check=True,timeout=180)
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def setUp(self):
        self.review=Path(tempfile.mkdtemp(dir=self.root))
        self.pair=[]
        for name in ("landscape","vertical"):
            temp=self.review/(name+"-acting-review.partial.mp4")
            target=self.review/(name+"-acting-review.mp4")
            shutil.copyfile(self.media,temp)
            target.write_bytes(b"Previously verified old original Rovor draft")
            self.pair.append((name,temp,target))
        self.sizes={"landscape":(320,180),"vertical":(320,180)}
    def tearDown(self):
        shutil.rmtree(self.review,ignore_errors=True)
    def run_promotion(self):
        return promote(self.pair,self.ffmpeg,self.wav,0,1872,self.review,
                       self.sha,sizes=self.sizes)
    def test_success_requires_two_verified_full_31s_exports(self):
        r=self.run_promotion()
        self.assertEqual(r["status"],"TWO_FORMAT_RENDERED_MEDIA_TECHNICALLY_VERIFIED")
        self.assertEqual(r["landscape"]["decodedFrames"],1872)
        self.assertEqual(r["portrait"]["decodedFrames"],1872)
        self.assertFalse(r["publicationApproved"])
        self.assertTrue((self.review/"final-media-integrity.json").exists())
        self.assertFalse((self.review/"final-media-integrity.partial.json").exists())
        for _,tmp,dest in self.pair:
            self.assertFalse(tmp.exists())
            self.assertEqual(hashlib.sha256(dest.read_bytes()).hexdigest(),
                             hashlib.sha256(self.media.read_bytes()).hexdigest())
    def test_bad_portrait_does_not_replace_previous_review(self):
        _,second,_=self.pair[1]
        subprocess.run([self.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y",
            "-i",str(self.media),"-t","3","-c","copy",str(second)],
            check=True,timeout=80)
        with self.assertRaises(ValueError):
            self.run_promotion()
        self.assertFalse((self.review/"final-media-integrity.json").exists())
        for _,_,dest in self.pair:
            self.assertEqual(dest.read_bytes(),b"Previously verified old original Rovor draft")
    def test_changed_audio_before_approval_cannot_be_published(self):
        with self.assertRaises(ValueError):
            promote(self.pair,self.ffmpeg,self.wav,0,1872,self.review,
                    "0"*64,sizes=self.sizes)
        self.assertFalse((self.review/"final-media-integrity.json").exists())
    def test_missing_second_orientation_rejected(self):
        with self.assertRaises(ValueError):
            promote(self.pair[:1],self.ffmpeg,self.wav,0,1872,self.review,
                    self.sha,sizes=self.sizes)
    def test_media_path_escape_rejected(self):
        bad=list(self.pair)
        bad[0]=(bad[0][0],self.media,bad[0][2])
        with self.assertRaises(ValueError):
            promote(bad,self.ffmpeg,self.wav,0,1872,self.review,
                    self.sha,sizes=self.sizes)


if __name__=="__main__":unittest.main()
