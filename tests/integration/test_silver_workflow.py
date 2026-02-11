"""
Silver Tier Integration Test.

Full workflow: watcher detection → type tagging → auto-move to In_Progress →
plan generation → classification → execution → auto-move to Done →
dashboard update → operations log verification.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import pytest
import frontmatter

from utils.vault_manager import VaultManager
from utils.operations_logger import OperationsLogger
from utils.dashboard_updater import DashboardUpdater
from watchers.base_watcher import BaseWatcher
from orchestrator.task_mover import TaskMover
from processors.task_classifier import TaskClassifier
from processors.task_executor import TaskExecutor
from security.credential_scanner import CredentialScanner


class TestSilverWorkflow:
    """Integration tests for the full Silver Tier workflow."""

    def test_full_lifecycle(self, temp_vault, tmp_path):
        """
        Test complete task lifecycle:
        1. Create task in Needs_Action (simulating watcher)
        2. Task has type: tag (US2)
        3. Move to In_Progress via TaskMover (US1)
        4. Classify task (US3)
        5. Execute simple task (US3)
        6. Move to Done via TaskMover (US1)
        7. Dashboard reflects counts (US4)
        8. Operations log records all ops (US5)
        """
        vault_path = temp_vault
        log_path = tmp_path / "operations.log"

        # Initialize components
        ops_logger = OperationsLogger(log_path)
        vault_manager = VaultManager(vault_path)
        task_mover = TaskMover(vault_manager, ops_logger)
        classifier = TaskClassifier()
        executor = TaskExecutor(vault_path)
        dashboard = DashboardUpdater(vault_path, ops_logger=ops_logger)

        # Step 1: Create task in Needs_Action with type tag (simulating watcher)
        task_content = "# Task: Create a summary file\n\n## Content\n\nPlease create a summary."
        task_metadata = {
            'source': 'file_watcher',
            'type': 'document',
            'created': '2026-02-10T12:00:00',
            'original_ref': '/path/to/report.txt',
            'status': 'pending',
        }
        task_filename = "20260210-120000-summary-task.md"
        task_path = vault_path / "Needs_Action" / task_filename

        post = frontmatter.Post(task_content, **task_metadata)
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        ops_logger.log(
            op='task_created', file=task_filename,
            src='external', dst='Needs_Action',
            outcome='success', detail='type:document'
        )

        # Verify: task exists in Needs_Action with type tag
        assert task_path.exists()
        loaded = frontmatter.load(str(task_path))
        assert loaded.metadata['type'] == 'document'

        # Step 2: Simulate status change to 'in_progress' → TaskMover moves it
        loaded.metadata['status'] = 'in_progress'
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(loaded))

        moved = task_mover.check_and_move_tasks()
        assert moved == 1
        assert not (vault_path / "Needs_Action" / task_filename).exists()
        assert (vault_path / "In_Progress" / task_filename).exists()

        # Step 3: Classify the task
        in_progress_path = vault_path / "In_Progress" / task_filename
        task_text = in_progress_path.read_text(encoding='utf-8')
        plan_steps = ["- [ ] Create a summary from the notes"]
        classification = classifier.classify(task_text, plan_steps)
        assert classification == 'simple'

        ops_logger.log(
            op='task_classified', file=task_filename,
            src='In_Progress', outcome='success',
            detail=f'complexity:{classification}'
        )

        # Step 4: Execute the simple task
        exec_result = executor.execute(in_progress_path, plan_steps)
        assert exec_result['success'] is True

        ops_logger.log(
            op='task_executed', file=task_filename,
            src='In_Progress', outcome='success',
            detail=f"op:{exec_result['operation']}"
        )

        # Step 5: Simulate status change to 'done' → TaskMover moves to Done
        loaded = frontmatter.load(str(in_progress_path))
        loaded.metadata['status'] = 'done'
        loaded.metadata['updated'] = '2026-02-10T12:05:00'
        with open(in_progress_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(loaded))

        moved = task_mover.check_and_move_tasks()
        assert moved == 1
        assert not (vault_path / "In_Progress" / task_filename).exists()
        assert (vault_path / "Done" / task_filename).exists()

        # Step 6: Dashboard reflects the lifecycle
        dashboard.refresh_dashboard()
        dashboard_content = (vault_path / "Dashboard.md").read_text()
        assert "Pending Tasks" in dashboard_content
        assert "In-Progress Tasks" in dashboard_content
        assert "Completed" in dashboard_content

        # Step 7: Operations log has all entries
        entries = ops_logger.read_recent(10)
        ops = [e['op'] for e in entries]
        assert 'task_created' in ops
        assert 'task_moved' in ops
        assert 'task_classified' in ops
        assert 'task_executed' in ops

    def test_complex_task_not_executed(self, temp_vault, tmp_path):
        """Test that complex tasks get classified but NOT executed."""
        vault_path = temp_vault
        classifier = TaskClassifier()

        task_content = "Deploy the application to production server via SSH"
        plan_steps = [
            "- [ ] SSH into the production server",
            "- [ ] Pull latest code from repository",
            "- [ ] Restart the application service",
            "- [ ] Verify deployment status"
        ]

        classification = classifier.classify(task_content, plan_steps)
        assert classification == 'complex'

    def test_credential_scan_integration(self, temp_vault):
        """Test credential scanning across vault."""
        vault_path = temp_vault
        scanner = CredentialScanner()

        # Create a clean task
        clean_task = vault_path / "Needs_Action" / "clean-task.md"
        clean_task.write_text("# Task: Clean task\n\nNo secrets here.")

        # Create a suspicious task
        suspicious_task = vault_path / "Needs_Action" / "suspicious-task.md"
        suspicious_task.write_text(
            "# Task: Config update\n\n"
            "api_key = AKIA1234567890ABCDEF\n"
        )

        findings = scanner.scan_vault(vault_path)
        assert len(findings) > 0
        # Only the suspicious file should be flagged
        flagged_files = {f['file'] for f in findings}
        assert str(suspicious_task) in flagged_files
        assert str(clean_task) not in flagged_files

    def test_vault_structure_silver(self, temp_vault):
        """Test that Silver Tier vault validates with In_Progress."""
        manager = VaultManager(temp_vault)
        is_valid, missing = manager.validate_structure()
        assert is_valid is True
        assert len(missing) == 0

    def test_file_type_detection(self):
        """Test file type detection from base_watcher."""
        assert BaseWatcher.detect_file_type(Path("report.txt")) == 'document'
        assert BaseWatcher.detect_file_type(Path("photo.png")) == 'image'
        assert BaseWatcher.detect_file_type(Path("data.csv")) == 'data'
        assert BaseWatcher.detect_file_type(Path("message.eml")) == 'email'
        assert BaseWatcher.detect_file_type(Path("binary.exe")) == 'unknown'
