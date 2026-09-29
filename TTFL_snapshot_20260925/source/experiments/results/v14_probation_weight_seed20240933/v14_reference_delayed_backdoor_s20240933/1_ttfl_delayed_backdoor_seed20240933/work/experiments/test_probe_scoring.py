"""Target-class preference is not evidence of a trigger-induced change."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.probe_scoring import calibrate_trigger_scores


class ProbeScoringTest(unittest.TestCase):
    def test_legacy_exact(self):
        self.assertEqual(calibrate_trigger_scores(.91, .2, None, 'legacy'), (.91, .2))

    def test_unconditional_target_bias(self):
        self.assertEqual(calibrate_trigger_scores(.99, .99, .99, 'clean_delta'), (0, 0))

    def test_trigger_increase_retained(self):
        br, tl = calibrate_trigger_scores(.95, .13, .1, 'clean_delta')
        self.assertAlmostEqual(br, .85)
        self.assertAlmostEqual(tl, .03)

    def test_negative_change_not_suspicious(self):
        self.assertEqual(calibrate_trigger_scores(.1, .2, .3, 'clean_delta'), (0, 0))

    def test_missing_nonfinite_out_of_range_rejected(self):
        for clean in (None, float('nan'), float('inf'), -1, 1.1):
            with self.assertRaises(ValueError):
                calibrate_trigger_scores(.8, .7, clean, 'clean_delta')

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            calibrate_trigger_scores(.8, .7, .1, 'other')


if __name__ == '__main__':
    unittest.main()
