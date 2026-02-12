"""Unit tests for Platinum Audit Trail (US7, T066)."""

import json
import pytest
from pathlib import Path
from utils.operations_logger import OperationsLogger


class TestPlatinumOpsRegistered:
    """Verify all 8 Platinum operation types are in VALID_OPS."""

    PLATINUM_OPS = [
        'sla_prediction', 'risk_scored', 'self_heal_retry',
        'self_heal_alternative', 'self_heal_partial', 'learning_update',
        'priority_adjusted', 'concurrency_queued',
    ]

    @pytest.mark.parametrize("op", PLATINUM_OPS)
    def test_op_in_valid_ops(self, op):
        assert op in OperationsLogger.VALID_OPS


class TestPlatinumAuditLogging:
    def _logger(self, tmp_path):
        path = tmp_path / "ops.log"
        return OperationsLogger(path), path

    def test_platinum_entry_has_src_field(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='sla_prediction', file='t.md', src='sla_predictor',
               outcome='success', detail='prob=0.8')
        entry = json.loads(path.read_text().strip().split('\n')[-1])
        assert entry['src'] == 'sla_predictor'

    def test_detail_field_contains_info(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='risk_scored', file='t.md', src='risk_engine',
               outcome='success', detail='composite=0.72')
        entry = json.loads(path.read_text().strip().split('\n')[-1])
        assert 'composite' in entry['detail']

    def test_self_heal_strategies_log(self, tmp_path):
        ol, path = self._logger(tmp_path)
        for op in ('self_heal_retry', 'self_heal_alternative', 'self_heal_partial'):
            ol.log(op=op, file='t.md', src='self_heal', outcome='success')
        lines = [json.loads(l) for l in path.read_text().strip().split('\n')]
        ops = [l['op'] for l in lines]
        assert 'self_heal_retry' in ops
        assert 'self_heal_alternative' in ops
        assert 'self_heal_partial' in ops

    def test_mixed_gold_platinum_valid_jsonl(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='task_created', file='t.md', src='watcher', outcome='success')
        ol.log(op='sla_prediction', file='t.md', src='sla_predictor',
               outcome='success', detail='prob=0.3')
        ol.log(op='task_executed', file='t.md', src='executor', outcome='success')
        ol.log(op='learning_update', file='t.md', src='learning_engine',
               outcome='success', detail='count=5')
        lines = path.read_text().strip().split('\n')
        assert len(lines) == 4
        for line in lines:
            parsed = json.loads(line)
            assert 'op' in parsed
            assert 'ts' in parsed

    def test_gold_entries_without_platinum_src_parse(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='task_created', file='t.md', src='Needs_Action', outcome='success')
        entry = json.loads(path.read_text().strip())
        assert entry['op'] == 'task_created'
        assert 'src' in entry

    def test_concurrency_queued_logs(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='concurrency_queued', file='t.md',
               src='concurrency_controller', outcome='success',
               detail='risk_score=0.65 queue_position=1')
        entry = json.loads(path.read_text().strip())
        assert entry['op'] == 'concurrency_queued'
        assert 'risk_score' in entry['detail']

    def test_priority_adjusted_logs(self, tmp_path):
        ol, path = self._logger(tmp_path)
        ol.log(op='priority_adjusted', file='t.md',
               src='risk_engine', outcome='success',
               detail='old_pos=3 new_pos=1')
        entry = json.loads(path.read_text().strip())
        assert entry['op'] == 'priority_adjusted'
