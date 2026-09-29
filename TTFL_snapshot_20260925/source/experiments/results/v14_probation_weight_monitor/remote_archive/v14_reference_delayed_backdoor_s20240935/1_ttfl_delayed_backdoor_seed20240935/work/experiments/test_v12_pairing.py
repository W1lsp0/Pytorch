"""Prevent the previous cross-scenario and cross-environment report errors."""
import copy
import unittest
from report_v12_matched import FIXED, SWITCHES, validate_manifests


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.base = {k: 1 for k in FIXED}
        self.base.update(scenario='delayed_backdoor', python='/local/env/bin/python', seed=20240933)
        self.base.update({k: False for k in SWITCHES})
        self.candidate = copy.deepcopy(self.base)
        self.candidate.update({k: True for k in SWITCHES})
        self.candidate.update(risk_soft_probation_c2_streak=3, risk_low_entropy_probe_h=0.15,
                              risk_low_entropy_probe_acc=0.1, risk_low_entropy_probe_streak=2)

    def test_matched(self):
        validate_manifests(self.base, self.candidate)

    def test_reject_wrong_scenario(self):
        self.base['scenario'] = 'none'
        with self.assertRaisesRegex(ValueError, 'scenario'):
            validate_manifests(self.base, self.candidate)

    def test_reject_cross_environment(self):
        self.base['python'] = '/remote/env/bin/python'
        with self.assertRaisesRegex(ValueError, 'python'):
            validate_manifests(self.base, self.candidate)

    def test_reject_wrong_seed(self):
        self.base['seed'] = 20240932
        with self.assertRaisesRegex(ValueError, 'seed'):
            validate_manifests(self.base, self.candidate)


if __name__ == '__main__':
    unittest.main()
