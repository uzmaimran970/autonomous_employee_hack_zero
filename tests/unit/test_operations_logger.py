"""
Unit tests for OperationsLogger.
"""

import json
import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.operations_logger import OperationsLogger


class TestOperationsLogger:
    """Tests for OperationsLogger class."""

    def test_init(self, tmp_path):
        """Test OperationsLogger initialization."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)
        assert logger.log_path == log_path

    def test_init_creates_parent_dirs(self, tmp_path):
        """Test that init creates parent directories if needed."""
        log_path = tmp_path / "subdir" / "nested" / "ops.jsonl"
        logger = OperationsLogger(log_path)
        assert log_path.parent.exists()

    def test_log_writes_json_line(self, tmp_path):
        """Test that log() writes a valid JSON line."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        result = logger.log(
            op='task_created',
            file='test-task.md',
            src='file_watcher',
            dst='Needs_Action',
            outcome='success',
            detail='Task created from file watcher'
        )

        assert result is True
        assert log_path.exists()

        content = log_path.read_text()
        lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry['op'] == 'task_created'
        assert entry['file'] == 'test-task.md'
        assert entry['src'] == 'file_watcher'
        assert entry['dst'] == 'Needs_Action'
        assert entry['outcome'] == 'success'
        assert entry['detail'] == 'Task created from file watcher'
        assert 'ts' in entry

    def test_log_multiple_entries(self, tmp_path):
        """Test that multiple log() calls append entries."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='task1.md', src='watcher')
        logger.log(op='task_moved', file='task1.md', src='Needs_Action', dst='In_Progress')
        logger.log(op='task_executed', file='task1.md', src='In_Progress')

        content = log_path.read_text()
        lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
        assert len(lines) == 3

        # Verify each line is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert 'op' in entry
            assert 'file' in entry

    def test_log_default_dst_is_null(self, tmp_path):
        """Test that dst defaults to 'null' string when not provided."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='task.md', src='watcher')

        content = log_path.read_text()
        entry = json.loads(content.strip())
        assert entry['dst'] == 'null'

    def test_read_recent_returns_entries(self, tmp_path):
        """Test read_recent() returns entries in newest-first order."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='task1.md', src='watcher')
        logger.log(op='task_moved', file='task2.md', src='Needs_Action', dst='In_Progress')
        logger.log(op='task_executed', file='task3.md', src='In_Progress')

        entries = logger.read_recent(n=50)
        assert len(entries) == 3
        # Newest first
        assert entries[0]['file'] == 'task3.md'
        assert entries[1]['file'] == 'task2.md'
        assert entries[2]['file'] == 'task1.md'

    def test_read_recent_limit(self, tmp_path):
        """Test read_recent() respects the n limit."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        for i in range(10):
            logger.log(op='task_created', file=f'task{i}.md', src='watcher')

        entries = logger.read_recent(n=3)
        assert len(entries) == 3
        # Should be the last 3 entries, newest first
        assert entries[0]['file'] == 'task9.md'
        assert entries[1]['file'] == 'task8.md'
        assert entries[2]['file'] == 'task7.md'

    def test_read_recent_empty_log(self, tmp_path):
        """Test read_recent() returns empty list when no log file exists."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        entries = logger.read_recent()
        assert entries == []

    def test_count_errors_counts_failed_outcomes(self, tmp_path):
        """Test count_errors() counts entries with outcome='failed'."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='task1.md', src='watcher', outcome='success')
        logger.log(op='error', file='task2.md', src='executor', outcome='failed',
                    detail='Execution error')
        logger.log(op='task_moved', file='task3.md', src='Needs_Action', outcome='success')
        logger.log(op='error', file='task4.md', src='executor', outcome='failed',
                    detail='Another error')
        logger.log(op='credential_flagged', file='task5.md', src='scanner', outcome='flagged')

        count = logger.count_errors(hours=24)
        assert count == 2

    def test_count_errors_empty_log(self, tmp_path):
        """Test count_errors() returns 0 when no log file exists."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)
        assert logger.count_errors() == 0

    def test_get_errors_returns_error_entries(self, tmp_path):
        """Test get_errors() returns only entries with outcome='failed'."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='ok.md', src='watcher', outcome='success')
        logger.log(op='error', file='bad1.md', src='executor', outcome='failed',
                    detail='Error one')
        logger.log(op='task_moved', file='ok2.md', src='Needs_Action', outcome='success')
        logger.log(op='error', file='bad2.md', src='executor', outcome='failed',
                    detail='Error two')

        errors = logger.get_errors(n=5)
        assert len(errors) == 2
        # Newest first
        assert errors[0]['file'] == 'bad2.md'
        assert errors[0]['detail'] == 'Error two'
        assert errors[1]['file'] == 'bad1.md'
        assert errors[1]['detail'] == 'Error one'

    def test_get_errors_limit(self, tmp_path):
        """Test get_errors() respects the n limit."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        for i in range(10):
            logger.log(op='error', file=f'err{i}.md', src='executor',
                        outcome='failed', detail=f'Error {i}')

        errors = logger.get_errors(n=3)
        assert len(errors) == 3

    def test_get_errors_empty_log(self, tmp_path):
        """Test get_errors() returns empty list when no log file exists."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)
        assert logger.get_errors() == []

    def test_get_errors_no_errors(self, tmp_path):
        """Test get_errors() returns empty list when no errors logged."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='ok.md', src='watcher', outcome='success')
        logger.log(op='task_moved', file='ok2.md', src='Needs_Action', outcome='success')

        errors = logger.get_errors()
        assert errors == []

    def test_log_entry_has_timestamp(self, tmp_path):
        """Test that each log entry has a timestamp field."""
        log_path = tmp_path / "ops.jsonl"
        logger = OperationsLogger(log_path)

        logger.log(op='task_created', file='task.md', src='watcher')

        entries = logger.read_recent()
        assert len(entries) == 1
        assert 'ts' in entries[0]
        # Timestamp should contain a date-like string
        assert 'T' in entries[0]['ts']
