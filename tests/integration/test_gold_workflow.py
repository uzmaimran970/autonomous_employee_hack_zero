"""
Gold Tier Integration Tests.

Full workflow tests for Gold Tier features:
- Multi-step lifecycle with 6-gate classification
- Rollback on failure
- Priority-based execution ordering
- SLA breach detection
- Dashboard metrics accuracy
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import pytest
import frontmatter

from utils.operations_logger import OperationsLogger
from utils.dashboard_updater import DashboardUpdater
from processors.task_processor import TaskProcessor
from processors.task_classifier import TaskClassifier
from processors.task_executor import TaskExecutor
from orchestrator.rollback_manager import RollbackManager
from orchestrator.sla_tracker import SLATracker
from notifications.notifier import NoOpNotifier


def _create_task(vault_path, filename, content, metadata):
    """Helper: write a task file with frontmatter into Needs_Action."""
    task_path = vault_path / "Needs_Action" / filename
    post = frontmatter.Post(content, **metadata)
    with open(task_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post))
    return task_path


class TestGoldWorkflow:
    """Integration tests for the full Gold Tier workflow."""

    # ------------------------------------------------------------------ T078
    def test_multi_step_lifecycle(self, temp_vault, tmp_path):
        """
        T078: Full Gold lifecycle — classify, snapshot, execute, done.

        1. Create a simple task in Needs_Action
        2. classify_and_execute runs 6-gate classification
        3. Simple task auto-executes (file_create)
        4. Task status becomes 'done'
        5. Operations log records task_classified + task_executed
        6. Gate results are stored in frontmatter
        """
        vault_path = temp_vault
        log_path = tmp_path / "ops.log"
        ops_logger = OperationsLogger(log_path)

        # Enable auto-execution for simple tasks
        config_overrides = {
            'auto_execute_simple': True,
            'auto_execute_complex': False,
            'rollback_retention_days': 7,
        }

        with patch('processors.task_processor.get_config', return_value=config_overrides):
            processor = TaskProcessor(
                vault_path, ops_logger=ops_logger,
                notifier=NoOpNotifier(), sla_tracker=None,
            )

        task_content = "# Task: Create summary report\n\nPlease create a summary."
        task_metadata = {
            'source': 'file_watcher',
            'type': 'document',
            'status': 'pending',
            'priority': 'normal',
            'created': datetime.now().isoformat(),
            'version': 1,
        }
        task_path = _create_task(
            vault_path, "20260211-100000-summary.md",
            task_content, task_metadata,
        )

        plan_steps = "- [ ] Create file summary_report.md with overview"

        with patch('processors.task_processor.get_config', return_value=config_overrides):
            result = processor.classify_and_execute(task_path, plan_steps)

        # Classification ran
        assert result is not None
        assert result['classification'] == 'simple'

        # Simple task was auto-executed
        assert result['executed'] is True
        assert result['execution_result']['success'] is True

        # Gate results recorded
        assert 'gate_results' in result
        assert isinstance(result['gate_results'], dict)

        # Operations log has both entries
        entries = ops_logger.read_recent(10)
        ops = [e['op'] for e in entries]
        assert 'task_classified' in ops
        assert 'task_executed' in ops

    # ------------------------------------------------------------------ T079
    def test_rollback_on_failure(self, temp_vault, tmp_path):
        """
        T079: Complex task failure triggers rollback.

        1. Create a complex task (many steps including disallowed ops)
        2. classify_and_execute creates snapshot before execution
        3. Execution fails on disallowed operation
        4. Rollback restores original task file
        5. Task status becomes 'failed_rollback'
        6. Rollback_Archive contains the snapshot with manifest.json
        """
        vault_path = temp_vault
        log_path = tmp_path / "ops.log"
        ops_logger = OperationsLogger(log_path)

        config_overrides = {
            'auto_execute_simple': True,
            'auto_execute_complex': True,
            'rollback_retention_days': 7,
        }

        with patch('processors.task_processor.get_config', return_value=config_overrides):
            processor = TaskProcessor(
                vault_path, ops_logger=ops_logger,
                notifier=NoOpNotifier(), sla_tracker=None,
            )

        task_content = (
            "# Task: Deploy production\n\n"
            "Deploy the application to production server via SSH."
        )
        task_metadata = {
            'source': 'file_watcher',
            'type': 'document',
            'status': 'pending',
            'priority': 'high',
            'created': datetime.now().isoformat(),
            'version': 1,
        }
        task_path = _create_task(
            vault_path, "20260211-110000-deploy.md",
            task_content, task_metadata,
        )

        # 6+ steps → complex (Gate 1 fails)
        plan_steps = (
            "- [ ] SSH into production server\n"
            "- [ ] Pull latest code from repository\n"
            "- [ ] Run database migrations\n"
            "- [ ] Restart application service\n"
            "- [ ] Verify health endpoint\n"
            "- [ ] Send deployment notification"
        )

        with patch('processors.task_processor.get_config', return_value=config_overrides):
            result = processor.classify_and_execute(task_path, plan_steps)

        assert result is not None
        assert result['classification'] == 'complex'
        assert result['executed'] is True

        # Execution should fail (SSH / network ops not in allowlist)
        assert result['execution_result']['success'] is False

        # Rollback_Archive should contain a snapshot directory
        archive = vault_path / "Rollback_Archive"
        snapshot_dirs = [d for d in archive.iterdir() if d.is_dir()]
        assert len(snapshot_dirs) >= 1

        # Snapshot has manifest.json and task.md
        snapshot = snapshot_dirs[0]
        assert (snapshot / "manifest.json").exists()
        assert (snapshot / "task.md").exists()

        # Ops log records rollback_triggered
        entries = ops_logger.read_recent(20)
        ops = [e['op'] for e in entries]
        assert 'rollback_triggered' in ops

    # ------------------------------------------------------------------ T080
    def test_priority_ordering(self, temp_vault, tmp_path):
        """
        T080: Critical tasks are processed before normal tasks.

        1. Create 3 tasks with different priorities (normal, critical, low)
        2. suggest_execution_sequence returns critical first
        3. Ordering: critical > normal > low
        """
        vault_path = temp_vault
        log_path = tmp_path / "ops.log"
        ops_logger = OperationsLogger(log_path)

        config_overrides = {
            'auto_execute_simple': False,
            'auto_execute_complex': False,
            'rollback_retention_days': 7,
        }

        with patch('processors.task_processor.get_config', return_value=config_overrides):
            processor = TaskProcessor(
                vault_path, ops_logger=ops_logger,
                notifier=NoOpNotifier(), sla_tracker=None,
            )

        # Create 3 tasks with varying priorities
        _create_task(vault_path, "task-normal.md",
                     "# Task: Normal priority task", {
                         'status': 'pending', 'priority': 'normal',
                         'source': 'file_watcher', 'version': 1,
                     })
        _create_task(vault_path, "task-critical.md",
                     "# Task: Critical priority task", {
                         'status': 'pending', 'priority': 'critical',
                         'source': 'file_watcher', 'version': 1,
                     })
        _create_task(vault_path, "task-low.md",
                     "# Task: Low priority task", {
                         'status': 'pending', 'priority': 'low',
                         'source': 'file_watcher', 'version': 1,
                     })

        pending = processor.read_pending_tasks()
        assert len(pending) >= 3

        ordered = processor.suggest_execution_sequence(pending)

        # Find positions of our tasks in the sorted list
        names = [p.name for p in ordered]
        critical_idx = names.index("task-critical.md")
        normal_idx = names.index("task-normal.md")
        low_idx = names.index("task-low.md")

        # Critical must come before normal, normal before low
        assert critical_idx < normal_idx, "Critical task must be processed before normal"
        assert normal_idx < low_idx, "Normal task must be processed before low"

    # ------------------------------------------------------------------ T081
    def test_sla_breach_detection(self, temp_vault, tmp_path):
        """
        T081: SLA breach is detected and logged when task exceeds threshold.

        1. Create a completed task with classified_at far in the past
        2. SLATracker.check_sla detects breach (duration > threshold)
        3. Ops log records sla_breach event
        4. Result dict has breach=True, compliant=False
        """
        vault_path = temp_vault
        log_path = tmp_path / "ops.log"
        ops_logger = OperationsLogger(log_path)

        config = {
            'sla_simple_minutes': 2,
            'sla_complex_minutes': 10,
        }
        sla_tracker = SLATracker(config=config, ops_logger=ops_logger)

        # Create a task that took way too long (classified 30 min ago, completed now)
        classified_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        completed_time = datetime.now().isoformat()

        task_metadata = {
            'status': 'done',
            'complexity': 'simple',
            'classified_at': classified_time,
            'completed_at': completed_time,
            'version': 2,
        }
        task_path = vault_path / "Done" / "20260211-sla-breach.md"
        post = frontmatter.Post("# Task: Slow task", **task_metadata)
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        result = sla_tracker.check_sla(task_path)

        # Breach detected
        assert result['breach'] is True
        assert result['compliant'] is False
        assert result['duration_minutes'] > config['sla_simple_minutes']
        assert result['threshold_minutes'] == config['sla_simple_minutes']

        # Ops log has sla_breach entry
        entries = ops_logger.read_recent(10)
        ops = [e['op'] for e in entries]
        assert 'sla_breach' in ops

        # Verify the breach entry has correct detail
        breach_entry = next(e for e in entries if e['op'] == 'sla_breach')
        assert 'duration:' in breach_entry['detail']
        assert 'threshold:' in breach_entry['detail']
        assert 'complexity:simple' in breach_entry['detail']

    # ------------------------------------------------------------------ T082
    def test_dashboard_metrics_accuracy(self, temp_vault, tmp_path):
        """
        T082: Dashboard metrics (rollback count, SLA compliance, throughput).

        1. Populate ops log with known events
        2. DashboardUpdater computes correct counts
        3. Rollback incidents count matches
        4. SLA compliance % is correct
        5. Throughput reflects completed tasks
        """
        vault_path = temp_vault
        log_path = tmp_path / "ops.log"
        ops_logger = OperationsLogger(log_path)

        # Simulate 3 successful executions and 1 rollback in the ops log
        ops_logger.log(
            op='task_executed', file='task-a.md',
            src='In_Progress', outcome='success',
            detail='op:file_create complexity:simple',
        )
        ops_logger.log(
            op='task_executed', file='task-b.md',
            src='In_Progress', outcome='success',
            detail='op:summarize complexity:simple',
        )
        ops_logger.log(
            op='task_executed', file='task-c.md',
            src='In_Progress', outcome='failed',
            detail='op:unknown complexity:complex',
        )
        ops_logger.log(
            op='rollback_triggered', file='task-c.md',
            src='In_Progress', dst='Rollback_Archive',
            outcome='success', detail='snapshot:20260211-task-c',
        )
        ops_logger.log(
            op='sla_breach', file='task-b.md',
            src='sla_tracker', outcome='flagged',
            detail='duration:5.0min threshold:2min complexity:simple',
        )

        dashboard = DashboardUpdater(vault_path, ops_logger=ops_logger)

        # Rollback incidents: 1
        assert dashboard.count_rollback_incidents(hours=24) == 1

        # SLA compliance: 3 executed, 1 breach → (3-1)/3 = 66.7%
        sla_str = dashboard.compute_sla_compliance(hours=24)
        assert '66.7%' in sla_str
        assert '3 tasks' in sla_str

        # Throughput: 2 successful in 24h
        throughput_str = dashboard.compute_throughput(hours=24)
        assert '2 in 24h' in throughput_str

        # Active alerts: should flag the rollback + sla_breach + execution failure
        alerts_str = dashboard.compute_active_alerts()
        assert 'Rollback triggered' in alerts_str or 'SLA breach' in alerts_str

        # Full dashboard refresh works without error
        assert dashboard.refresh_dashboard() is True
        content = (vault_path / "Dashboard.md").read_text()
        assert 'Rollback Incidents' in content
        assert 'SLA Compliance' in content
        assert 'Throughput' in content
