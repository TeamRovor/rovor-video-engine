"""No paid dependencies or media uploads; 30-900s story-chapter regressions."""
import csv
import tempfile
import unittest
from pathlib import Path

from longform_chapters import plan,make_plan,read_energy,MIN_VIDEO_SECONDS

def envelope(duration,bursts=()):
    samples=[]
    for i in range(round(duration*100)):
        t=i/100
        db=-20.
        for a,b in bursts:
            if a<=t<=b:db=-52.
        samples.append((round(t,2),db))
    return samples

class ChapterTests(unittest.TestCase):
    def test_8_minute_frame_exactness(self):
        result=plan(480,envelope(480,[(54.5,55.5),(109.5,110.5),(164.5,165.5)]))
        self.assertEqual(result["totalTimelineFrames"],28800)
        self.assertEqual(result["chapters"][0]["startFrame"],0)
        self.assertEqual(result["chapters"][-1]["endFrameExclusive"],28800)
        self.assertEqual(sum(x["decodedFramesTarget"] for x in result["chapters"]),28800)
        self.assertGreaterEqual(result["chapterCount"],7)
        self.assertFalse(result["artisticApproval"])
        for row in result["chapters"]:
            self.assertGreaterEqual(row["decodedFramesTarget"],1800)
            self.assertLessEqual(row["decodedFramesTarget"],4200)
            self.assertFalse(row["originalSceneAssetsVerified"])
            self.assertEqual(row["visualPlanStatus"],"UNWRITTEN")
        for a,b in zip(result["chapters"],result["chapters"][1:]):
            self.assertEqual(a["endFrameExclusive"],b["startFrame"])

    def test_9_minute_rounded_audio_duration(self):
        result=plan(540.008,envelope(540.01))
        self.assertEqual(result["totalTimelineFrames"],32401)
        self.assertAlmostEqual(result["chapters"][-1]["sourceAudioEndSeconds"],540.008,places=3)
        self.assertEqual(result["chapters"][-1]["endFrameExclusive"],32401)

    def test_exact_minimum_and_below(self):
        result=plan(30,envelope(30))
        self.assertEqual(result["chapterCount"],1)
        self.assertEqual(result["totalTimelineFrames"],1800)
        with self.assertRaises(ValueError):plan(29.999,envelope(30))

    def test_final_chapter_must_not_be_tiny(self):
        for duration in (70.01,82,90,101,120,135,170,221,500,899):
            result=plan(duration,envelope(duration))
            self.assertEqual(result["chapters"][-1]["endFrameExclusive"],
                             result["totalTimelineFrames"])
            self.assertTrue(all(x["decodedFramesTarget"]>=1800 for x in result["chapters"]))

    def test_cut_is_only_review_candidate(self):
        result=plan(150,envelope(150,[(54.7,55.3)]))
        self.assertEqual(result["chapters"][0]["boundaryAfter"]["type"],"low-energy-candidate")
        self.assertTrue(result["chapters"][0]["boundaryAfter"]["requiresAudibleWordBoundaryReview"])
        with_no_silence=plan(150,envelope(150))
        self.assertEqual(with_no_silence["chapters"][0]["boundaryAfter"]["type"],
                         "timing-only-REQUIRES-LISTENING")
        self.assertTrue(with_no_silence["chapters"][0]["boundaryAfter"]["requiresAudibleWordBoundaryReview"])

    def test_nonfinite_and_too_long_rejected(self):
        for value in (0,25,901,float("nan"),float("inf")):
            with self.assertRaises(ValueError):plan(value,envelope(31))
        with self.assertRaises(ValueError):plan(60,[(0.,float("nan"))])
        with self.assertRaises(ValueError):plan(60,[])
        with self.assertRaises(ValueError):plan(60,envelope(60),fps=30)

    def test_csv_bounds_and_atomic_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            csv_file=Path(d)/"waveform-10ms.csv"
            with csv_file.open("w",newline="") as f:
                writer=csv.writer(f)
                writer.writerow(("time_sec","rms","peak","rms_dbfs"))
                for t,db in envelope(85,[(54.8,55.2)]):
                    writer.writerow((t,.1,.2,db))
            parsed=read_energy(csv_file,85)
            self.assertEqual(len(parsed),8500)
            result=make_plan(85,csv_file,Path(d)/"chapters.json")
            self.assertEqual(result["totalTimelineFrames"],5100)
            self.assertTrue((Path(d)/"chapters.json").is_file())
            self.assertFalse((Path(d)/"chapters.json.partial").exists())
            with csv_file.open("a") as f:f.write("5,.1,.2,-2\n")
            with self.assertRaises(ValueError):read_energy(csv_file,85)

    def test_not_synthetic_pad_and_output_unapproved(self):
        r=plan(66,envelope(66))
        self.assertEqual(r["chapterCount"],1)
        self.assertFalse(r["originalNarrationModified"])
        self.assertFalse(r["phonemeAlignmentCertified"])
        self.assertFalse(r["speechTranscriptVerified"])
        self.assertEqual(r["kind"],"PREPRODUCTION-ONLY")

if __name__=="__main__":unittest.main()
