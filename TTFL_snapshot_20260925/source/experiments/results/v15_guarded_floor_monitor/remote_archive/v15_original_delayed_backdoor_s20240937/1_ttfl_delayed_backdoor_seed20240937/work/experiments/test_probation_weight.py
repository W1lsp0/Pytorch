import unittest
from unittest.mock import patch
from server.risk_weighting import risk_weight_factor
from server.trust_manager import TrustScoreManager

class WeightTests(unittest.TestCase):
    def test_disabled_preserves_legacy(self):
        for r in (0,.25,.9,1):
            for p in (0,.5,1,2):
                self.assertEqual(risk_weight_factor(r,p,True,0),max(0,1-r)**p)
    def test_floor_only_applies_in_probation(self):
        self.assertEqual(risk_weight_factor(1,1,True,.25),.25)
        self.assertEqual(risk_weight_factor(1,1,False,.25),0)
        self.assertEqual(risk_weight_factor(.1,1,True,.25),.9)
    def test_invalid_floor_rejected(self):
        for floor in (-.1,1.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):risk_weight_factor(.5,1,True,floor)
    @patch.dict('os.environ',{'TTFL_DISABLE_DB':'1','RISK_LOW_ENTROPY_PROBE_GUARD':'1'})
    def test_nonzero_factor_does_not_clear_hard_isolation(self):
        tm=TrustScoreManager();entry=tm._ensure_history_entry('a')
        entry['low_entropy_probe_streak']=tm.risk_low_entropy_probe_streak_limit
        self.assertEqual(risk_weight_factor(1,1,True,.25),.25)
        self.assertTrue(tm.is_risk_hard_isolated('a'))
        entry['low_entropy_probe_streak']=0
        entry['c2_quarantine_streak']=tm.c2_memory_quarantine_rounds
        self.assertTrue(tm.is_risk_hard_isolated('a'))
        entry['c2_quarantine_streak']=0;tm.blacklist.add('a')
        self.assertTrue(tm.is_risk_hard_isolated('a'))

if __name__=='__main__':unittest.main()
