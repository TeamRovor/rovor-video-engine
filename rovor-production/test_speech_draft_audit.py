"""Whisper English draft must NEVER be confused with verified phoneme timecodes."""
import csv
import tempfile
import unittest
from pathlib import Path
from speech_draft_audit import audit,extract


def whisper(rows):
    return {"transcription":[{"text":text,"offsets":{"from":int(a*1000),"to":int(b*1000)}}
                             for a,b,text in rows]}


def chapters(duration=120):
    return {"kind":"PREPRODUCTION-ONLY","recordingDurationSeconds":duration,
            "chapters":[{"chapter":i+1,"sourceAudioStartSeconds":60*i,
                         "sourceAudioEndSeconds":60*(i+1)} for i in range(round(duration/60))]}


class SpeechReviewTests(unittest.TestCase):
    def test_8min_transcription_can_be_audited_without_certification(self):
        source=whisper([(0,24,"Welcome to the Rovor Digital expedition."),
                        (55,65,"One word might cross this arbitrary scene cut."),
                        (250,270,"This animated idea needs an original illustration."),
                        (505,507.8,"That brings our real narration to its end.")])
        ch={"kind":"PREPRODUCTION-ONLY","recordingDurationSeconds":507.8727,
            "chapters":[{"chapter":1,"sourceAudioStartSeconds":0.,
                         "sourceAudioEndSeconds":60.},
                        {"chapter":2,"sourceAudioStartSeconds":60.,
                         "sourceAudioEndSeconds":507.8727}]}
        out=audit(source,507.8727,ch)
        self.assertEqual(out["segmentCount"],4)
        self.assertEqual(len(out["chapterBoundaryConcerns"]),1)
        self.assertEqual(out["chapterBoundaryConcerns"][0]["ASRSegmentsCrossingBoundary"],[1])
        self.assertFalse(out["transcriptHumanVerified"])
        self.assertFalse(out["phonemeBoundariesCertified"])
        self.assertFalse(out["canDriveFinalMouthAnimation"])
        self.assertTrue(out["longAsrGaps"])
    def test_repeated_long_whisper_hallucination_flagged(self):
        line="This sentence has exactly the same hallucinated words again"
        out=audit(whisper([(0,4,line),(4.2,8,line),(8.2,12,line)]),22)
        self.assertTrue(all("same-long-phrase-repeated-three-times" in row["reviewFlags"]
                            for row in out["segments"]))
    def test_english_whisper_offsets_are_milliseconds(self):
        out=audit(whisper([(0,3,"The website has an original character.")]),22.047375)
        self.assertEqual(out["segments"][0]["endSeconds"],3)
    def test_asr_text_not_spoken_in_near_silence_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"waveform.csv"
            with path.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(("time_sec","rms_dbfs"))
                for i in range(300):
                    w.writerow((i/100.,-59.))
            out=audit(whisper([(0,2.9,"Rovor is speaking but the room is silent")]),3,
                      waveform=path)
            self.assertIn("asr-text-mostly-below-48dbfs",out["segments"][0]["reviewFlags"])
    def test_overlaps_flagged_not_misreported_as_forced_phonemes(self):
        out=audit(whisper([(1,3,"New website"),(2.7,5,"An animated browser")]),12)
        self.assertIn("asr-timestamp-overlap",out["segments"][1]["reviewFlags"])
    def test_empty_whisper_segments_do_not_crash(self):
        out=audit(whisper([(0,.5," "),(1,2,"one actual word")]),10)
        self.assertEqual(out["segmentCount"],1)
        self.assertEqual(out["segments"][0]["text"],"one actual word")
    def test_real_whisper_final_padding_is_truncated_not_filled(self):
        result=audit(whisper([(0,5,"Some English words."),
                              (19.44,22.4,"The actual recording ends right here.")]),22.047375)
        tail=result["segments"][-1]
        self.assertEqual(tail["endSeconds"],22.047)
        self.assertIn("whisper-end-extends-past-real-recording-truncated",tail["reviewFlags"])
        self.assertFalse(result["phonemeBoundariesCertified"])
        self.assertFalse(result["canDriveFinalMouthAnimation"])

    def test_large_false_future_whisper_segment_rejected(self):
        with self.assertRaises(ValueError):
            audit(whisper([(0,5,"Spoken words"),(19.44,26.0,"Impossible fake continuation")]),22.047375)

    def test_invalid_asr_segment_timestamps_rejected(self):
        for rows in [[(4,5,"later"),(1,2,"earlier")],
                     [(1,3,"too long")],[(2,2,"zero")],
                     [(-1,2,"negative")]]:
            with self.assertRaises(ValueError):
                audit(whisper(rows),2)
    def test_mismatched_preproduction_chapter_plan_rejected(self):
        with self.assertRaises(ValueError):
            audit(whisper([(0,2,"hello there")]),30,chapters(120))
    def test_empty_text_not_guess_missing_speech(self):
        out=audit({"transcription":[]},35)
        self.assertEqual(out["totalDraftWordCount"],0)
        self.assertFalse(out["canDriveFinalMouthAnimation"])
        self.assertEqual(len(out["longAsrGaps"]),1)
    def test_malformed_non_whisper_json_rejected(self):
        with self.assertRaises(ValueError):
            audit({"segments":[{"start":0,"text":"hi"}]},30)
    def test_no_audio_below_zero_or_above_15_minutes(self):
        with self.assertRaises(ValueError):
            audit(whisper([]),0)
        with self.assertRaises(ValueError):
            audit(whisper([]),901)


if __name__=="__main__":
    unittest.main()
