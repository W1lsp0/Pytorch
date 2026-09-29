import unittest

from report_risk_soft_probation import measure


class ProbationReportTest(unittest.TestCase):
    def fixture(self):
        manifest = dict(clients=3, rounds=4, malicious_client_ids=[1, 2],
                        attack_start_round=2, attack_stop_round=4,
                        scenario='delayed_backdoor', seed=1, risk_soft_probation=True)
        summary = dict(clean_accuracy=[.5]*4, backdoor_asr=[.1, .2, .4, .9])
        rows = [dict(round=n, risk_decision_audit={
            str(cid): dict(risk_isolated=True, blacklisted=False)
            for cid in range(3)}, client_layer_stats={
            '0': dict(included_layers=10),
            '1': dict(included_layers=0 if n in (1, 3, 4) else 10),
            '2': dict(included_layers=10)}) for n in range(1, 5)]
        return manifest, summary, rows

    def test_risk_flags_do_not_imply_blocking(self):
        result = measure(*self.fixture())
        self.assertEqual(result['normal_explicit_isolation_total'], 4)
        self.assertEqual(result['normal_excluded_total'], 0)
        self.assertEqual(result['malicious_isolated_rounds'], [1, 2, 3, 4])
        self.assertEqual(result['malicious_fully_excluded_rounds_by_client'],
                         {'1': [1, 3, 4], '2': []})

    def test_attack_window_and_pre_attack_exclusion(self):
        result = measure(*self.fixture())
        self.assertAlmostEqual(result['attack_window_mean_asr'], .3)
        self.assertEqual(result['attack_window_peak_asr'], .4)
        self.assertEqual(result['first_malicious_exclusion_after_start_by_client'],
                         {'1': 3, '2': None})
        self.assertEqual(result['malicious_excluded_before_attack_by_client'],
                         {'1': True, '2': False})


if __name__ == '__main__':
    unittest.main()
