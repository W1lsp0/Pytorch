"""Reject corrupt or incomplete scoring evidence before reporting a result."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from report_trigger_delta import validate_frozen_source, validate_scores


class TriggerDeltaAuditTest(unittest.TestCase):
    def row(self):
        return dict(round=1, trigger_score_mode='clean_delta', client_layer_stats={'1': {}},
                    trigger_score_audit={'1': dict(mode='clean_delta', clean=.5, raw_br=.75,
                        raw_tl=.25, effective_br=.25, effective_tl=0)})

    def test_complete_pair(self):
        self.assertEqual(validate_scores(self.row()), 1)

    def test_missing_baseline_evidence(self):
        row = self.row()
        row['trigger_score_audit'].clear()
        with self.assertRaises(AssertionError):
            validate_scores(row)

    def test_uncalibrated_score_is_rejected(self):
        row = self.row()
        row['trigger_score_audit']['1']['effective_br'] = .75
        with self.assertRaises(AssertionError):
            validate_scores(row)

    def test_nonfinite_score_is_rejected(self):
        row = self.row()
        row['trigger_score_audit']['1']['clean'] = float('nan')
        with self.assertRaises(AssertionError):
            validate_scores(row)

    def test_unknown_scoring_mode_is_rejected(self):
        row = self.row()
        row['trigger_score_mode'] = 'legacy'
        with self.assertRaises(AssertionError):
            validate_scores(row)

    def test_changed_frozen_source_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            run = Path(tmp)
            (run/'work').mkdir()
            path = run/'work/config.py'
            path.write_text('seed = 1\n')
            protocol = dict(source_files={'config.py': hashlib.sha256(path.read_bytes()).hexdigest()})
            validate_frozen_source(run, protocol)
            path.write_text('seed = 2\n')
            with self.assertRaises(AssertionError):
                validate_frozen_source(run, protocol)


if __name__ == '__main__':
    unittest.main()
