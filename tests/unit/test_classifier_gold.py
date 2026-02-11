"""
Unit tests for Gold Tier 6-gate classifier.

Tests Gates 4-6, manual_review, gate_results structure,
and sequential gate short-circuiting.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from processors.task_classifier import TaskClassifier


def make_steps(n):
    """Generate n actionable plan steps."""
    return [f'- [ ] Step {i+1}: Create file "output{i}.txt"' for i in range(n)]


GOLD_CONFIG = {
    'allowed_external_services': [],
    'sla_simple_minutes': 2,
    'sla_complex_minutes': 10,
}


class TestGate4Permissions(unittest.TestCase):
    """Gate 4: Permission check against allowlist and vault scope."""

    def setUp(self):
        self.vault_dir = Path(tempfile.mkdtemp())
        (self.vault_dir / 'Rollback_Archive').mkdir()

    def tearDown(self):
        shutil.rmtree(self.vault_dir, ignore_errors=True)

    @patch('processors.task_classifier.get_config')
    def test_no_network_refs_passes(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Create a file', make_steps(3))
        self.assertEqual(result, 'simple')
        self.assertEqual(tc.get_gate_results()['gate_4_permissions'], 'pass')

    @patch('processors.task_classifier.get_config')
    def test_network_ref_blocked_empty_allowlist(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Call the http api endpoint', make_steps(3))
        self.assertEqual(result, 'complex')
        self.assertEqual(tc.get_gate_results()['gate_4_permissions'], 'fail')

    @patch('processors.task_classifier.get_config')
    def test_network_ref_allowed_service_passes(self, mock_config):
        cfg = GOLD_CONFIG.copy()
        cfg['allowed_external_services'] = ['myapi.com']
        mock_config.return_value = cfg
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Call the http myapi.com endpoint', make_steps(3))
        self.assertEqual(result, 'simple')
        self.assertEqual(tc.get_gate_results()['gate_4_permissions'], 'pass')

    @patch('processors.task_classifier.get_config')
    def test_network_ref_unknown_service_blocked(self, mock_config):
        cfg = GOLD_CONFIG.copy()
        cfg['allowed_external_services'] = ['myapi.com']
        mock_config.return_value = cfg
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Call the http evil.com endpoint', make_steps(3))
        self.assertEqual(result, 'complex')
        self.assertEqual(tc.get_gate_results()['gate_4_permissions'], 'fail')


class TestGate5SLAFeasibility(unittest.TestCase):
    """Gate 5: SLA feasibility estimation."""

    def setUp(self):
        self.vault_dir = Path(tempfile.mkdtemp())
        (self.vault_dir / 'Rollback_Archive').mkdir()

    def tearDown(self):
        shutil.rmtree(self.vault_dir, ignore_errors=True)

    @patch('processors.task_classifier.get_config')
    def test_no_history_passes(self, mock_config):
        """Empty history = assume feasible."""
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Create file', make_steps(3))
        self.assertEqual(result, 'simple')
        self.assertEqual(tc.get_gate_results()['gate_5_sla'], 'pass')

    @patch('processors.task_classifier.get_config')
    def test_with_ops_logger_no_data_passes(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        mock_logger = MagicMock()
        mock_logger.read_recent.return_value = []
        tc = TaskClassifier(vault_path=self.vault_dir, ops_logger=mock_logger)
        result = tc.classify('Create file', make_steps(3))
        self.assertEqual(result, 'simple')
        self.assertEqual(tc.get_gate_results()['gate_5_sla'], 'pass')


class TestGate6RollbackReadiness(unittest.TestCase):
    """Gate 6: Rollback readiness check."""

    def setUp(self):
        self.vault_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.vault_dir, ignore_errors=True)

    @patch('processors.task_classifier.get_config')
    def test_rollback_archive_exists_passes(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        (self.vault_dir / 'Rollback_Archive').mkdir()
        tc = TaskClassifier(vault_path=self.vault_dir)
        # Complex task (8 steps) should check gate 6
        result = tc.classify('Create file', make_steps(8))
        self.assertEqual(result, 'complex')
        self.assertEqual(tc.get_gate_results()['gate_6_rollback'], 'pass')

    @patch('processors.task_classifier.get_config')
    def test_rollback_archive_missing_fails(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier(vault_path=self.vault_dir)
        # Complex task without Rollback_Archive
        result = tc.classify('Create file', make_steps(8))
        self.assertEqual(result, 'complex')
        self.assertEqual(tc.get_gate_results()['gate_6_rollback'], 'fail')

    @patch('processors.task_classifier.get_config')
    def test_simple_task_skips_gate6(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier(vault_path=self.vault_dir)
        result = tc.classify('Create file', make_steps(3))
        self.assertEqual(result, 'simple')
        self.assertIn('skipped', tc.get_gate_results()['gate_6_rollback'])


class TestManualReview(unittest.TestCase):
    """Classification for tasks exceeding MAX_COMPLEX_STEPS."""

    @patch('processors.task_classifier.get_config')
    def test_over_15_steps_is_manual_review(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier()
        result = tc.classify('Big task', make_steps(20))
        self.assertEqual(result, 'manual_review')

    @patch('processors.task_classifier.get_config')
    def test_exactly_15_steps_is_complex(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        vault_dir = Path(tempfile.mkdtemp())
        (vault_dir / 'Rollback_Archive').mkdir()
        tc = TaskClassifier(vault_path=vault_dir)
        result = tc.classify('Medium task', make_steps(15))
        self.assertEqual(result, 'complex')
        shutil.rmtree(vault_dir, ignore_errors=True)


class TestGateResults(unittest.TestCase):
    """gate_results dict structure."""

    @patch('processors.task_classifier.get_config')
    def test_all_6_gate_keys_present(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        vault_dir = Path(tempfile.mkdtemp())
        (vault_dir / 'Rollback_Archive').mkdir()
        tc = TaskClassifier(vault_path=vault_dir)
        tc.classify('Create file', make_steps(3))
        gates = tc.get_gate_results()
        expected_keys = {
            'gate_1_step_count', 'gate_2_credentials', 'gate_3_determinism',
            'gate_4_permissions', 'gate_5_sla', 'gate_6_rollback',
        }
        self.assertEqual(set(gates.keys()), expected_keys)
        shutil.rmtree(vault_dir, ignore_errors=True)

    @patch('processors.task_classifier.get_config')
    def test_simple_task_all_pass(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        vault_dir = Path(tempfile.mkdtemp())
        (vault_dir / 'Rollback_Archive').mkdir()
        tc = TaskClassifier(vault_path=vault_dir)
        tc.classify('Create file', make_steps(3))
        gates = tc.get_gate_results()
        self.assertEqual(gates['gate_1_step_count'], 'pass')
        self.assertEqual(gates['gate_2_credentials'], 'pass')
        self.assertEqual(gates['gate_3_determinism'], 'pass')
        self.assertEqual(gates['gate_4_permissions'], 'pass')
        self.assertEqual(gates['gate_5_sla'], 'pass')
        shutil.rmtree(vault_dir, ignore_errors=True)


class TestGateShortCircuit(unittest.TestCase):
    """Gates short-circuit: failure skips remaining gates."""

    @patch('processors.task_classifier.get_config')
    def test_gate2_failure_skips_3_4_5_6(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier()
        tc.classify('Task with password in it', make_steps(3))
        gates = tc.get_gate_results()
        self.assertEqual(gates['gate_1_step_count'], 'pass')
        self.assertEqual(gates['gate_2_credentials'], 'fail')
        self.assertEqual(gates['gate_3_determinism'], 'skipped')
        self.assertEqual(gates['gate_4_permissions'], 'skipped')
        self.assertEqual(gates['gate_5_sla'], 'skipped')
        self.assertEqual(gates['gate_6_rollback'], 'skipped')

    @patch('processors.task_classifier.get_config')
    def test_gate3_failure_skips_4_5_6(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier()
        tc.classify('Normal task', ['- [ ] Download file from network'])
        gates = tc.get_gate_results()
        self.assertEqual(gates['gate_2_credentials'], 'pass')
        self.assertEqual(gates['gate_3_determinism'], 'fail')
        self.assertEqual(gates['gate_4_permissions'], 'skipped')

    @patch('processors.task_classifier.get_config')
    def test_manual_review_skips_all_remaining(self, mock_config):
        mock_config.return_value = GOLD_CONFIG.copy()
        tc = TaskClassifier()
        tc.classify('Huge task', make_steps(20))
        gates = tc.get_gate_results()
        self.assertIn('fail:manual_review', gates['gate_1_step_count'])
        self.assertEqual(gates['gate_2_credentials'], 'skipped')
        self.assertEqual(gates['gate_6_rollback'], 'skipped')


if __name__ == '__main__':
    unittest.main()
