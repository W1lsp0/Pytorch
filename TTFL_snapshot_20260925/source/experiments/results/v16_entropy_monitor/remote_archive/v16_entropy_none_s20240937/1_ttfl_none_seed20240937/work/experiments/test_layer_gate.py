import os
import unittest
import numpy as np
from server.sensitivity import calculate_layer_sensitivities

class LayerGateTest(unittest.TestCase):
    def test_lambda_is_explicit_and_monotonic(self):
        data={'0': {'weights':[np.ones(4),np.ones(4)], 'trust_score':0.6}}
        old=os.environ.get('TTFL_LAYER_GATE_LAMBDA')
        try:
            os.environ['TTFL_LAYER_GATE_LAMBDA']='0.15'; high=calculate_layer_sensitivities(data,[np.ones(4),np.ones(4)])
            os.environ['TTFL_LAYER_GATE_LAMBDA']='0.05'; low=calculate_layer_sensitivities(data,[np.ones(4),np.ones(4)])
            self.assertTrue(all(a['inclusion_threshold'] >= b['inclusion_threshold'] for a,b in zip(high,low)))
            self.assertLess(low[0]['inclusion_threshold'], high[0]['inclusion_threshold'])
        finally:
            if old is None: os.environ.pop('TTFL_LAYER_GATE_LAMBDA',None)
            else: os.environ['TTFL_LAYER_GATE_LAMBDA']=old

if __name__=='__main__': unittest.main()
