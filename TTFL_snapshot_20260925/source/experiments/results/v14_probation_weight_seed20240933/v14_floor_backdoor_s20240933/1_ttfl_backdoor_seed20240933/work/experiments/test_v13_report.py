import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from report_v13_layer_gate import write_reports, one
from report_v12_matched import FIXED as V12_FIXED
from watch_v13_layer import screen

TEST_ROOT=Path('/data1/lab409/W1lsp0/.t'); TEST_ROOT.mkdir(exist_ok=True)

class ReportTests(unittest.TestCase):
    def test_pending_paths_merge_and_do_not_claim_complete(self):
        with TemporaryDirectory(dir=TEST_ROOT) as d:
            root=Path(d); spec=root/'pairs.json'
            spec.write_text(json.dumps({'pairs':[dict(name='pair',baseline=str(root/'baseline'),candidate=str(root/'candidate'))]}))
            r=write_reports(spec)
            self.assertEqual(r['pairs'][0]['validation'],'pending')
            self.assertFalse(r['complete'])
            self.assertFalse(r['goal_achieved'])
    def test_different_environment_rejected_even_if_both_success(self):
        with TemporaryDirectory(dir=TEST_ROOT) as d:
            b,c=Path(d)/'b',Path(d)/'c'
            for p in (b,c):p.mkdir();(p/'completion.json').write_text('{"status":"success"}')
            bm={k:1 for k in V12_FIXED};bm.update(layer_gate_lambda=.15,python='env_a')
            cm=dict(bm,layer_gate_lambda=.05,python='env_b')
            (b/'manifest.json').write_text(json.dumps(bm));(c/'manifest.json').write_text(json.dumps(cm))
            with self.assertRaisesRegex(ValueError,'paired mismatch'):one(b,c)
    def test_final_asr_regression_rejects_good_mean_asr(self):
        r={'complete':True,'pairs':[dict(name='attack',scenario='backdoor',delta=dict(final_asr=.01,attack_window_mean_asr=-.1,attack_window_peak_asr=0,final_accuracy=.1,normal_mean_exclusion=-.1))]}
        self.assertEqual(screen(r)['status'],'not_met')
        self.assertEqual(screen(r)['regressions'][0]['metric'],'final_asr')
    def test_descriptive_pass_is_not_research_success(self):
        r={'complete':True,'pairs':[dict(name='attack',scenario='backdoor',delta=dict(final_asr=-.01,attack_window_mean_asr=-.1,attack_window_peak_asr=0,final_accuracy=.1,normal_mean_exclusion=-.1))]}
        self.assertEqual(screen(r)['status'],'development_screen_passed')
        self.assertFalse(screen(r)['goal_achieved'])

if __name__=='__main__':unittest.main()
