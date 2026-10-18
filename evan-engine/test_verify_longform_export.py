"""Complete 31.2s source-voice, 60fps final-export smoke test, local only.

These are synthetic fixture files in a temporary directory and are never
presented to the user as an original Rovor cartoon.
"""
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
import numpy as np
from verify_longform_export import verify,_correlate_window,duration_wav,FPS


def write_wav(path,seconds):
    n=round(seconds*16000)
    t=np.arange(n,dtype=np.float32)/16000
    # Changing harmonic energy, deterministic impulses and multi-formant
    # oscillation expose duplicated/reordered/shifted narration windows.
    rng=np.random.default_rng(9062)
    envelope=(.28+.18*np.sin(2*np.pi*.7*t))*(.75+.25*np.sin(2*np.pi*.11*t))
    wave_values=(np.sin(2*np.pi*(180*t+13*t*t/seconds))+
                 .28*np.sin(2*np.pi*430*t)+
                 .035*rng.normal(0,1,size=n))
    pcm=np.rint(np.clip(envelope*wave_values,-.8,.8)*32767).astype("<i2")
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(pcm.tobytes())


class FinalVideoIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exe=os.environ.get("ROVOR_TEST_FFMPEG","")
        if not exe or not Path(exe).is_file():
            raise unittest.SkipTest("FFmpeg must be explicitly supplied by Mac")
        cls.ffmpeg=exe
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        cls.wav=cls.root/"source-31.2sec.wav"
        cls.movie=cls.root/"31.2sec-fixture.mp4"
        write_wav(cls.wav,31.2)
        subprocess.run([
            exe,"-nostdin","-hide_banner","-loglevel","error","-y",
            "-f","lavfi","-i","color=c=black:s=320x180:r=60:d=31.2",
            "-i",str(cls.wav),"-map","0:v:0","-map","1:a:0",
            "-c:v","libx264","-preset","ultrafast","-crf","35","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","160k","-shortest",str(cls.movie)
        ],check=True,timeout=200)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
    def test_full_video_has_true_contiguous_60fps_and_real_matched_voice(self):
        report=verify(self.ffmpeg,self.movie,self.wav,size=(320,180))
        self.assertEqual(report["decodedFrames"],math.ceil(31.2*FPS))
        self.assertTrue(report["decodedPtsMonotonicAndAt60Fps"])
        self.assertGreaterEqual(report["voiceWindowsVerified"],3)
        self.assertTrue(report["sourceAudioPreserved"])
        self.assertFalse(report["readyForPublicRelease"])
        self.assertFalse(report["sourcePhonemesCertified"])
    def test_under_30_seconds_source_does_not_count_as_deliverable(self):
        tiny=self.root/"22sec.wav"
        write_wav(tiny,22)
        with self.assertRaises(ValueError):
            verify(self.ffmpeg,self.movie,tiny,size=(320,180))
    def test_short_video_cannot_claim_complete_long_voiceover(self):
        short=self.root/"short.mp4"
        subprocess.run([self.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y",
            "-i",str(self.movie),"-t","2","-c","copy",str(short)],
            check=True,timeout=100)
        with self.assertRaises(ValueError):
            verify(self.ffmpeg,short,self.wav,size=(320,180))
    def test_wrong_source_audio_rejected_at_distributed_windows(self):
        other=self.root/"wrong-take.wav"
        n=round(31.2*16000)
        rng=np.random.default_rng(7)
        pcm=np.rint(rng.normal(0,.16,n).clip(-.9,.9)*32767).astype("<i2")
        with wave.open(str(other),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(pcm.tobytes())
        with self.assertRaises(ValueError):
            verify(self.ffmpeg,self.movie,other,size=(320,180))
    def test_original_32s_excerpt_from_70s_narration_is_matched_at_source_offset(self):
        long_audio=self.root/"70seconds-unmodified.wav"
        video=self.root/"32seconds-from-real-offset.mp4"
        write_wav(long_audio,70)
        subprocess.run([
            self.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y",
            "-f","lavfi","-i","color=c=black:s=320x180:r=60:d=32",
            "-ss","18","-i",str(long_audio),"-map","0:v:0","-map","1:a:0",
            "-t","32","-c:v","libx264","-preset","ultrafast","-crf","35",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
            str(video)],check=True,timeout=200)
        out=verify(self.ffmpeg,video,long_audio,size=(320,180),
                   start_frame=18*60,end_frame=50*60)
        self.assertEqual(out["selectedStartFrame"],1080)
        self.assertEqual(out["decodedFrames"],1920)
        self.assertGreaterEqual(out["voiceWindowsVerified"],3)
        with self.assertRaises(ValueError):
            verify(self.ffmpeg,video,long_audio,size=(320,180),
                   start_frame=19*60,end_frame=51*60)

    def test_relative_shift_is_detected_in_nonrepeating_speech(self):
        rng=np.random.default_rng(2)
        reference=rng.normal(0,1,20000).astype(np.float32)
        shifted=np.concatenate([np.zeros(500,dtype=np.float32),reference[:-500]])
        result=_correlate_window(reference,shifted,limit=640)
        self.assertEqual(result["lagSamples"],500)
        self.assertGreater(result["correlation"],.99)
    def test_output_dimensions_are_never_assumed_from_filename(self):
        with self.assertRaises(ValueError):
            verify(self.ffmpeg,self.movie,self.wav,size=(999,999))
    def test_source_audio_is_immutable_pcm_reference(self):
        samples,duration=duration_wav(self.wav)
        self.assertEqual(samples,round(31.2*16000))
        self.assertAlmostEqual(duration,31.2,places=4)


if __name__=="__main__":
    unittest.main()
