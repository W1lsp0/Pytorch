"""Guard independent validation against protocol drift and duplicate conditions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from report_risk_gate_independent import index, validate_pair_manifest

ROOT=Path(__file__).resolve().parent

class PairAuditTest(unittest.TestCase):
    def setUp(self):
        self.baseline=json.loads((ROOT/'results/v5_risk_gate_independent_baseline_seed20240927/1_ttfl_none_seed20240927/manifest.json').read_text())
        self.candidate=copy.deepcopy(self.baseline)
        self.candidate['risk_raw_attenuation_power']=0.0

    def test_valid_actual_manifest(self):
        validate_pair_manifest(self.candidate,self.baseline,20240927)

    def test_wrong_power_or_seed(self):
        for key,value in [('risk_raw_attenuation_power',1.0),('seed',20240925)]:
            changed=copy.deepcopy(self.candidate); changed[key]=value
            with self.assertRaises(AssertionError):
                validate_pair_manifest(changed,self.baseline,20240927)

    def test_unplanned_protocol_changes(self):
        for key,value in [('poison_rate',.2),('attack_start_round',2),('server_proxy_size',400),('local_epochs',2),('known_trigger_probe',False),('heavy_probe_rotate_mod',5)]:
            changed=copy.deepcopy(self.candidate); changed[key]=value
            with self.assertRaises(AssertionError):
                validate_pair_manifest(changed,self.baseline,20240927)

    def test_duplicate_scenario_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root=Path(temp)
            for name in ('a','b'):
                (root/name).mkdir()
                (root/name/'manifest.json').write_text(json.dumps(self.baseline))
            with self.assertRaises(AssertionError):
                index(root)

if __name__=='__main__': unittest.main()
