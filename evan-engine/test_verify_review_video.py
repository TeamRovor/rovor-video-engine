import unittest
import numpy as np
from verify_review_video import verify_frames,compare_audio

class ReviewVerificationTests(unittest.TestCase):
    def checksums(self,rows):
        return '#tb 0: 1/60\n#dimensions 0: 1920x1080\n'+''.join(f'0,{d},{p},{duration},12,hash\n' for d,p,duration in rows)
    def test_continuous_frames(self):
        self.assertEqual(verify_frames(self.checksums([(0,0,1),(1,1,1)]),(1920,1080),60,2)['decodedFrames'],2)
    def test_missing_or_repeated_timestamp_refused(self):
        for rows in ([(0,0,1),(2,2,1)],[(0,0,1),(0,0,1)]):
            with self.assertRaises(ValueError):verify_frames(self.checksums(rows),(1920,1080),60,2)
    def test_wrong_geometry_and_count_refused(self):
        for size,count in (((1080,1920),2),((1920,1080),3)):
            with self.assertRaises(ValueError):verify_frames(self.checksums([(0,0,1),(1,1,1)]),size,60,count)
    def test_lossy_voice_match_accepted(self):
        rng=np.random.default_rng(31);voice=rng.normal(size=16000)
        result=compare_audio(voice*.95+rng.normal(scale=.002,size=16000),voice)
        self.assertEqual(result['offsetSamples'],0);self.assertGreater(result['referenceCorrelation'],.99)
    def test_different_or_offset_audio_refused(self):
        rng=np.random.default_rng(31);voice=rng.normal(size=16000)
        for audio in (rng.normal(size=16000),np.r_[np.zeros(160),voice[:-160]],np.zeros(16000)):
            with self.assertRaises(ValueError):compare_audio(audio,voice)

if __name__=='__main__':unittest.main()
