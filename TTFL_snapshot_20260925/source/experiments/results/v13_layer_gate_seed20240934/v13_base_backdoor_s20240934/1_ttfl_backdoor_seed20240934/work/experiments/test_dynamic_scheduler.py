import unittest
from supervise_dynamic import choose_gpu

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.gpus={str(i):dict(free_mib=23000, used_mib=23, utilization=0, compute_pids=[]) for i in range(3)}
    def test_foreign_idle_process_excluded(self):
        self.gpus['0']['compute_pids']=[99]
        self.assertEqual(choose_gpu(self.gpus,set(),21000),'1')
    def test_inflight_reserved_before_cuda_initializes(self):
        self.assertEqual(choose_gpu(self.gpus,{'0','1'},21000),'2')
    def test_busy_gpu_returns_to_queue_after_release(self):
        self.gpus['0'].update(free_mib=17000,used_mib=6028)
        self.assertIsNone(choose_gpu(self.gpus,{'1','2'},21000))
        self.gpus['0'].update(free_mib=23000,used_mib=23)
        self.assertEqual(choose_gpu(self.gpus,{'1','2'},21000),'0')
    def test_no_gpu_for_oversized_job(self):
        self.assertIsNone(choose_gpu(self.gpus,set(),24000))

if __name__=='__main__':unittest.main()
