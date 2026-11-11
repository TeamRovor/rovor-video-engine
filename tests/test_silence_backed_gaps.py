"""Tests for conservative gap classification against aligner silence spans."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from speech_plan_gate import audit


def plan(silences):
    return {
        'script': 'alpha beta',
        'alignment': {'status': 'acoustic', 'wordCoverage': 1.0},
        'words': [
            {'start': 0.0, 'end': 0.25, 'scriptIndex': 0,
             'word': 'alpha', 'reviewFlags': []},
            {'start': 0.75, 'end': 1.0, 'scriptIndex': 1,
             'word': 'beta', 'reviewFlags': []},
        ],
        'phonemes': [
            {'start': 0.0, 'end': 0.25, 'scriptIndex': 0,
             'word': 'alpha', 'phone': 'AA', 'value': 'D'},
            {'start': 0.75, 'end': 1.0, 'scriptIndex': 1,
             'word': 'beta', 'phone': 'B', 'value': 'A'},
        ],
        'silences': silences,
    }


class SilenceBackedGapTests(unittest.TestCase):
    def test_fully_silence_covered_gap_is_confirmed_as_rest(self):
        result = audit(plan([{'start': 0.25, 'end': 0.75}]), 1.0, 60)
        self.assertEqual(result['status'], 'technical_pass_pending_visual_review')
        self.assertEqual(result['silenceBackedGapCount'], 1)
        self.assertFalse(any(f['type'] == 'phone-gap-needs-rest-review'
                             for f in result['reviewFlags']))

    def test_union_of_silences_can_cover_gap_with_frame_tolerance(self):
        result = audit(plan([
            {'start': 0.25, 'end': 0.48},
            {'start': 0.49, 'end': 0.75},
        ]), 1.0, 60)
        self.assertEqual(result['silenceBackedGapCount'], 1)
        self.assertEqual(result['reviewFlags'], [])

    def test_uncovered_or_partial_gap_remains_review_required(self):
        for spans in ([], [{'start': 0.25, 'end': 0.60} ],
                      [{'start': 0.28, 'end': 0.75} ]):
            with self.subTest(spans=spans):
                result = audit(plan(spans), 1.0, 60)
                self.assertEqual(result['status'], 'review_required')
                self.assertEqual(result['silenceBackedGapCount'], 0)
                self.assertEqual(result['reviewFlags'][0]['type'],
                                 'phone-gap-needs-rest-review')

    def test_invalid_silence_interval_cannot_clear_gap(self):
        result = audit(plan([{'start': 0.8, 'end': 0.2}]), 1.0, 60)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['silenceBackedGapCount'], 0)
        self.assertTrue(result['errors'])


if __name__ == '__main__':
    unittest.main()
