"""Shutdown recovery must reject unrelated launcher failures."""
import unittest
from watch_matrix import is_shutdown_timeout


class ShutdownRecoveryTest(unittest.TestCase):
    def test_explicit_timeout(self):
        for suffix in ('completed', 'completion'):
            text = f'Traceback...\nRuntimeError: clients did not exit after server {suffix}\n'
            self.assertTrue(is_shutdown_timeout({'error': 'launcher exited 1'}, text))

    def test_generic_failure(self):
        self.assertFalse(is_shutdown_timeout({'error': 'launcher exited 1'}, 'RuntimeError: GPU out of memory'))

    def test_conflicting_child_error(self):
        self.assertFalse(is_shutdown_timeout({'error': 'launcher exited 1'},
            'child process failed: server\nRuntimeError: clients did not exit after server completed'))

    def test_different_completion_error(self):
        self.assertFalse(is_shutdown_timeout({'error': 'matrix interrupted'},
            'RuntimeError: clients did not exit after server completed'))


if __name__ == '__main__':
    unittest.main()
