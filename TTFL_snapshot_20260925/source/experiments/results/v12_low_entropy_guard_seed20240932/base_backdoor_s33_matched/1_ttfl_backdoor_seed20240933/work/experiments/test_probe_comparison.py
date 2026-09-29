"""Checks for paired comparison direction, matching, and snapshot evidence."""
import statistics
import tempfile
import unittest
from pathlib import Path

from compare_probe_conditions import FIELDS, METRICS, check_manifests, mean_sd, paired_delta, training_hash


class ProbeComparisonTest(unittest.TestCase):
    def test_protocol_mismatch_is_rejected(self):
        off = dict.fromkeys(FIELDS, 1)
        on = dict(off)
        off.update(known_trigger_probe=False, heavy_probe_rotate_mod=5)
        on.update(known_trigger_probe=True, heavy_probe_rotate_mod=1)
        check_manifests(off, on)
        on['seed'] = 2
        with self.assertRaisesRegex(ValueError, 'seed'):
            check_manifests(off, on)

    def test_wrong_probe_condition_is_rejected(self):
        off = dict.fromkeys(FIELDS, 1)
        on = dict(off)
        off.update(known_trigger_probe=False, heavy_probe_rotate_mod=5)
        on.update(known_trigger_probe=True, heavy_probe_rotate_mod=5)
        with self.assertRaisesRegex(ValueError, 'rotation 1'):
            check_manifests(off, on)

    def test_difference_is_on_minus_off_in_percentage_points(self):
        off = dict.fromkeys(METRICS, .2)
        on = dict.fromkeys(METRICS, .1)
        off['attack_window_mean_asr'] = on['attack_window_mean_asr'] = None
        delta = paired_delta(off, on)
        self.assertAlmostEqual(delta['final_asr'], -10)
        self.assertIsNone(delta['attack_window_mean_asr'])

    def test_sd_is_computed_on_paired_differences(self):
        off = [.1, .5]
        on = [.2, .6]
        diffs = [100 * (b-a) for a,b in zip(off,on)]
        stats = mean_sd(diffs)
        self.assertAlmostEqual(stats['mean'], 10)
        self.assertAlmostEqual(stats['sd'], 0)
        self.assertGreater(statistics.stdev(on), .1)

    def test_missing_seed_does_not_become_zero(self):
        self.assertIsNone(mean_sd([None, None]))
        with self.assertRaises(ValueError):
            mean_sd([1, None])
        with self.assertRaises(ValueError):
            mean_sd([1])

    def test_training_hash_ignores_report_changes_but_detects_model_changes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            run = Path(tmp)
            work = run/'work'
            for d in ('server', 'Client', 'experiments'):
                (work/d).mkdir(parents=True)
            (work/'config.py').write_text('seed = 1\n')
            (work/'server/server.py').write_text('model = 1\n')
            before = training_hash(run)
            (work/'experiments/report.py').write_text('formatting = 2\n')
            self.assertEqual(before, training_hash(run))
            (work/'server/server.py').write_text('model = 2\n')
            self.assertNotEqual(before, training_hash(run))


if __name__ == '__main__':
    unittest.main()
