"""Tests for evidence-based blacklist reconstruction and unknown recovery state."""
import json
import tempfile
import unittest
from pathlib import Path

from audit_records import load_audit
from report_recovery import recovery_event


class AuditRecordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def records(self, text, included=False):
        rows = [dict(round=n, layer_count=2,
                     client_layer_stats={'1': dict(included_layers=2)} if included else {})
                for n in (1, 2, 3)]
        (self.root/'round_metrics.jsonl').write_text('\n'.join(map(json.dumps, rows)))
        (self.root/'server.log').write_text(text)
        return rows

    def test_exact_round_evidence_only_and_raw_immutable(self):
        self.records('第 2 轮 | 审计阶段开始...\n'
                     '[Client 1] 黑名单拦截: 该节点已被系统永久清退 (risk_threshold)\n'
                     '第 2 轮聚合完成\n'
                     '[Client 2] 黑名单拦截: 该节点已被系统永久清退 (outside_round)\n')
        original = (self.root/'round_metrics.jsonl').read_bytes()
        rows, p = load_audit(self.root)
        self.assertEqual(rows[0]['client_layer_stats'], {})
        self.assertEqual(rows[2]['client_layer_stats'], {})
        self.assertEqual(set(rows[1]['client_layer_stats']), {'1'})
        self.assertEqual(rows[1]['client_layer_stats']['1']['included_layers'], 0)
        self.assertEqual(p['blacklist_records_recovered'], [dict(round=2, client_id=1, reason='risk_threshold')])
        self.assertEqual((self.root/'round_metrics.jsonl').read_bytes(), original)

    def test_conflicting_inclusion_is_rejected(self):
        self.records('第 2 轮 | 审计阶段开始...\n[Client 1] 黑名单拦截: 清退 (reason)\n', included=True)
        with self.assertRaises(ValueError):
            load_audit(self.root)

    def test_missing_is_not_recovery(self):
        rows = self.records('')
        self.assertEqual(recovery_event(rows, '1', 1, 2)['status'], 'insufficient_audit')

    def test_recovered_client_then_relapse(self):
        rows = [dict(round=n, client_layer_stats={'1': dict(included_layers=inc)})
                for n, inc in enumerate([0, 0, 2, 0, 2], start=1)]
        event = recovery_event(rows, '1', 1, 3)
        self.assertEqual(event['recovery_delay_from_stop'], 0)
        self.assertEqual(event['relapse_rounds'], [4])
        self.assertEqual(event['stable_regained_round'], 5)


if __name__ == '__main__':
    unittest.main()
