import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from compare_probe_conditions import FIELDS
from report_v14_weight import one, write_reports

TMP='/data1/lab409/W1lsp0/.t'
class PairTests(unittest.TestCase):
    def test_floor_pair_validates_and_switch_drift_rejected(self):
        with TemporaryDirectory(dir=TMP) as tmp:
            b,c=Path(tmp)/'b',Path(tmp)/'c'
            m={k:1 for k in FIELDS};m.update(scenario='backdoor',seed=20240933,known_trigger_probe=True,heavy_probe_rotate_mod=1,trigger_score_mode='clean_delta',risk_raw_attenuation_power=1,risk_cross_channel_guard=False,layer_gate_lambda=.15,risk_soft_probation_c2_streak=3,risk_low_entropy_probe_h=.15,risk_low_entropy_probe_acc=.1,risk_low_entropy_probe_streak=2,risk_probation_weight_floor=0)
            for k in ('risk_soft_probation','risk_soft_probation_reference_exclude','risk_soft_probation_c2_exclude','risk_low_entropy_probe_guard'):m[k]=True
            for p,floor in ((b,0),(c,.25)):
                p.mkdir();(p/'completion.json').write_text('{"status":"success"}')
                (p/'manifest.json').write_text(json.dumps(dict(m,risk_probation_weight_floor=floor)))
            vals=dict(final_accuracy=.5,final_asr=.1,attack_window_mean_asr=.2,attack_window_peak_asr=.3,normal_mean_exclusion=.1,normal_ever_excluded_rate=.2)
            with patch('report_v14_weight.artifacts',return_value=dict(initial_sha256='x',partition_sha256='y',training_sha256='z')),patch('report_v14_weight.read_run',return_value=vals),patch('report_v14_weight.validate_schedule'):
                self.assertEqual(one(b,c,'floor_ablation')['validation'],'validated')
                cm=json.loads((c/'manifest.json').read_text());cm['risk_soft_probation_c2_streak']=9
                (c/'manifest.json').write_text(json.dumps(cm))
                with self.assertRaisesRegex(ValueError,'paired mismatch'):one(b,c,'floor_ablation')
    def test_pending_report_does_not_claim_success(self):
        with TemporaryDirectory(dir=TMP) as tmp:
            r=Path(tmp);p=r/'pairs.json';p.write_text(json.dumps({'pairs':[dict(name='n',baseline=str(r/'b'),candidate=str(r/'c'),comparison='floor_ablation')]}))
            d=write_reports(p);self.assertFalse(d['complete']);self.assertFalse(d['goal_achieved'])
            self.assertEqual(d['pairs'][0]['validation'],'pending')

if __name__=='__main__':unittest.main()
