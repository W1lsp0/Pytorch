import unittest
from report_cross_channel_guard import measure


class ReportSemantics(unittest.TestCase):
    def fixture(self, start=1, stop=0):
        manifest = dict(clients=2, rounds=30, malicious_client_ids=[1],
                        attack_start_round=start, attack_stop_round=stop,
                        scenario='backdoor', seed=123)
        summary = dict(clean_accuracy=[.5]*30, backdoor_asr=[n/100 for n in range(1,31)])
        rows = [dict(round=n, risk_decision_audit={
            '0': dict(risk_isolated=False, blacklisted=False),
            '1': dict(risk_isolated=n==17, blacklisted=False)},
            client_layer_stats={'0': dict(included_layers=0 if n==20 else 10),
                                '1': dict(included_layers=0 if n==17 else 10)}) for n in range(1,31)]
        return manifest, summary, rows

    def test_attack_windows_follow_manifest(self):
        self.assertAlmostEqual(measure(*self.fixture())['attack_window_mean_asr'], .155)
        self.assertAlmostEqual(measure(*self.fixture(11))['attack_window_mean_asr'], .205)
        self.assertAlmostEqual(measure(*self.fixture(11,21))['attack_window_mean_asr'], .155)

    def test_layer_rejection_is_not_explicit_isolation(self):
        result = measure(*self.fixture())
        self.assertEqual(result['normal_excluded_total'], 1)
        self.assertEqual(result['normal_explicit_isolation_total'], 0)

    def test_one_isolation_is_not_continuous(self):
        result = measure(*self.fixture())
        self.assertEqual(result['malicious_isolated_rounds'], [17])
        self.assertEqual(result['malicious_fully_excluded_rounds'], [17])


if __name__ == '__main__':
    unittest.main()
