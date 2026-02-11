"""
Unit tests for TaskMover.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

import frontmatter

from utils.vault_manager import VaultManager
from utils.operations_logger import OperationsLogger
from orchestrator.task_mover import TaskMover


class TestTaskMover:
    """Tests for TaskMover class."""

    def test_init(self, temp_vault):
        """Test TaskMover initialization."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)
        assert mover.vault_manager is vm
        assert mover.ops_logger is None

    def test_init_with_logger(self, temp_vault, tmp_path):
        """Test TaskMover initialization with OperationsLogger."""
        vm = VaultManager(temp_vault)
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)
        mover = TaskMover(vm, ops_logger=ops_logger)
        assert mover.ops_logger is ops_logger

    def test_check_and_move_no_tasks(self, temp_vault):
        """Test check_and_move_tasks with no tasks returns 0."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)
        moved = mover.check_and_move_tasks()
        assert moved == 0

    def test_move_in_progress_status_to_in_progress_folder(self, temp_vault):
        """Test that task with status='in_progress' in Needs_Action moves to In_Progress."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Create a task with status=in_progress in Needs_Action
        task_path = temp_vault / 'Needs_Action' / 'task-ip.md'
        post = frontmatter.Post(
            '# Task In Progress\n\nThis task should move to In_Progress.',
            status='in_progress',
            source='test',
            created='2026-02-10T12:00:00'
        )
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        moved = mover.check_and_move_tasks()
        assert moved == 1
        assert not task_path.exists()
        assert (temp_vault / 'In_Progress' / 'task-ip.md').exists()

    def test_move_done_status_from_in_progress_to_done(self, temp_vault):
        """Test that task with status='done' in In_Progress moves to Done."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Create a task with status=done in In_Progress
        task_path = temp_vault / 'In_Progress' / 'task-done.md'
        post = frontmatter.Post(
            '# Task Done\n\nThis task should move to Done.',
            status='done',
            source='test',
            created='2026-02-10T12:00:00'
        )
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        moved = mover.check_and_move_tasks()
        assert moved == 1
        assert not task_path.exists()
        assert (temp_vault / 'Done' / 'task-done.md').exists()

    def test_move_done_status_from_needs_action_to_done(self, temp_vault):
        """Test that task with status='done' in Needs_Action skips In_Progress and goes to Done."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Create a task with status=done in Needs_Action
        task_path = temp_vault / 'Needs_Action' / 'task-skip.md'
        post = frontmatter.Post(
            '# Task Skip\n\nThis task should go straight to Done.',
            status='done',
            source='test',
            created='2026-02-10T12:00:00'
        )
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        moved = mover.check_and_move_tasks()
        assert moved == 1
        assert not task_path.exists()
        assert (temp_vault / 'Done' / 'task-skip.md').exists()

    def test_pending_task_not_moved(self, temp_vault):
        """Test that task with status='pending' stays in Needs_Action."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Create a task with status=pending
        task_path = temp_vault / 'Needs_Action' / 'task-pending.md'
        post = frontmatter.Post(
            '# Pending Task\n\nThis task should stay.',
            status='pending',
            source='test',
            created='2026-02-10T12:00:00'
        )
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        moved = mover.check_and_move_tasks()
        assert moved == 0
        assert task_path.exists()

    def test_in_progress_task_stays_if_not_done(self, temp_vault):
        """Test that task with status='in_progress' in In_Progress stays."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Create a task with status=in_progress in In_Progress (correct location)
        task_path = temp_vault / 'In_Progress' / 'task-stay.md'
        post = frontmatter.Post(
            '# Staying Task\n\nThis task should not move.',
            status='in_progress',
            source='test',
            created='2026-02-10T12:00:00'
        )
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        moved = mover.check_and_move_tasks()
        assert moved == 0
        assert task_path.exists()

    def test_multiple_tasks_moved(self, temp_vault):
        """Test moving multiple tasks at once."""
        vm = VaultManager(temp_vault)
        mover = TaskMover(vm)

        # Task 1: in_progress in Needs_Action -> In_Progress
        post1 = frontmatter.Post('# Task 1', status='in_progress', source='test')
        with open(temp_vault / 'Needs_Action' / 'task1.md', 'w') as f:
            f.write(frontmatter.dumps(post1))

        # Task 2: done in In_Progress -> Done
        post2 = frontmatter.Post('# Task 2', status='done', source='test')
        with open(temp_vault / 'In_Progress' / 'task2.md', 'w') as f:
            f.write(frontmatter.dumps(post2))

        # Task 3: pending in Needs_Action -> stays
        post3 = frontmatter.Post('# Task 3', status='pending', source='test')
        with open(temp_vault / 'Needs_Action' / 'task3.md', 'w') as f:
            f.write(frontmatter.dumps(post3))

        moved = mover.check_and_move_tasks()
        assert moved == 2
        assert (temp_vault / 'In_Progress' / 'task1.md').exists()
        assert (temp_vault / 'Done' / 'task2.md').exists()
        assert (temp_vault / 'Needs_Action' / 'task3.md').exists()

    def test_operations_logger_records_moves(self, temp_vault, tmp_path):
        """Test that TaskMover logs moves to OperationsLogger."""
        vm = VaultManager(temp_vault)
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)
        mover = TaskMover(vm, ops_logger=ops_logger)

        # Create task to move
        post = frontmatter.Post('# Logged Task', status='in_progress', source='test')
        with open(temp_vault / 'Needs_Action' / 'logged.md', 'w') as f:
            f.write(frontmatter.dumps(post))

        mover.check_and_move_tasks()

        entries = ops_logger.read_recent()
        assert len(entries) >= 1
        move_entry = entries[0]
        assert move_entry['op'] == 'task_moved'
        assert move_entry['file'] == 'logged.md'
        assert move_entry['src'] == 'Needs_Action'
        assert move_entry['dst'] == 'In_Progress'
