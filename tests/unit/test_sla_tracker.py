"""Unit tests for SLATracker."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import frontmatter
from orchestrator.sla_tracker import SLATracker


class TestSLACheck(unittest.TestCase):
    """Test check_sla method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = {'sla_simple_minutes': 2, 'sla_complex_minutes': 10}

    def _create_task(self, classified_at, completed_at, complexity='simple'):
        path = Path(self.tmp) / 'task.md'
        post = frontmatter.Post('# Task', **{
            'status': 'done',
            'complexity': complexity,
            'classified_at': classified_at.isoformat(),
            'completed_at': completed_at.isoformat(),
        })
        path.write_text(frontmatter.dumps(post), encoding='utf-8')
        return path

    def test_compliant_simple_task(self):
        now = datetime.now()
        path = self._create_task(now - timedelta(minutes=1), now)
        tracker = SLATracker(config=self.config)
        result = tracker.check_sla(path)
        self.assertTrue(result['compliant'])
        self.assertFalse(result['breach'])

    def test_breach_simple_task(self):
        now = datetime.now()
        path = self._create_task(now - timedelta(minutes=5), now)
        tracker = SLATracker(config=self.config)
        result = tracker.check_sla(path)
        self.assertFalse(result['compliant'])
        self.assertTrue(result['breach'])

    def test_missing_timestamps_returns_compliant(self):
        path = Path(self.tmp) / 'task2.md'
        post = frontmatter.Post('# Task', status='done')
        path.write_text(frontmatter.dumps(post), encoding='utf-8')
        tracker = SLATracker(config=self.config)
        result = tracker.check_sla(path)
        self.assertTrue(result['compliant'])


class TestComputeCompliance(unittest.TestCase):
    """Test compute_compliance method."""

    def test_no_ops_logger_returns_100(self):
        tracker = SLATracker(config={'sla_simple_minutes': 2, 'sla_complex_minutes': 10})
        result = tracker.compute_compliance()
        self.assertEqual(result['compliance_pct'], 100.0)

    def test_empty_log_returns_100(self):
        mock_logger = MagicMock()
        mock_logger.read_recent.return_value = []
        tracker = SLATracker(
            config={'sla_simple_minutes': 2, 'sla_complex_minutes': 10},
            ops_logger=mock_logger
        )
        result = tracker.compute_compliance()
        self.assertEqual(result['compliance_pct'], 100.0)


class TestEstimateDuration(unittest.TestCase):
    """Test estimate_duration method."""

    def test_no_logger_returns_none(self):
        tracker = SLATracker(config={'sla_simple_minutes': 2, 'sla_complex_minutes': 10})
        self.assertIsNone(tracker.estimate_duration('simple'))

    def test_empty_log_returns_none(self):
        mock_logger = MagicMock()
        mock_logger.read_recent.return_value = []
        tracker = SLATracker(
            config={'sla_simple_minutes': 2, 'sla_complex_minutes': 10},
            ops_logger=mock_logger
        )
        self.assertIsNone(tracker.estimate_duration('simple'))


if __name__ == '__main__':
    unittest.main()
