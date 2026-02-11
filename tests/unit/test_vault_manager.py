"""
Unit tests for VaultManager.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.vault_manager import VaultManager


class TestVaultManager:
    """Tests for VaultManager class."""

    def test_init(self, temp_vault):
        """Test VaultManager initialization."""
        manager = VaultManager(temp_vault)
        assert manager.vault_path == temp_vault
        assert manager.needs_action_path == temp_vault / 'Needs_Action'
        assert manager.done_path == temp_vault / 'Done'
        assert manager.plans_path == temp_vault / 'Plans'

    def test_in_progress_path_init(self, temp_vault):
        """Test that In_Progress path is initialized correctly."""
        manager = VaultManager(temp_vault)
        assert manager.in_progress_path == temp_vault / 'In_Progress'
        assert manager.in_progress_path.exists()

    def test_validate_structure_valid(self, temp_vault):
        """Test validation with valid structure."""
        manager = VaultManager(temp_vault)
        is_valid, missing = manager.validate_structure()
        assert is_valid is True
        assert len(missing) == 0

    def test_validate_structure_missing_folder(self, temp_vault):
        """Test validation with missing folder."""
        import shutil
        shutil.rmtree(temp_vault / 'Plans')

        manager = VaultManager(temp_vault)
        is_valid, missing = manager.validate_structure()
        assert is_valid is False
        assert 'Folder: Plans' in missing

    def test_validate_structure_missing_file(self, temp_vault):
        """Test validation with missing file."""
        (temp_vault / 'Dashboard.md').unlink()

        manager = VaultManager(temp_vault)
        is_valid, missing = manager.validate_structure()
        assert is_valid is False
        assert 'File: Dashboard.md' in missing

    def test_validate_structure_with_in_progress(self, temp_vault):
        """Test validation detects missing In_Progress folder."""
        import shutil
        shutil.rmtree(temp_vault / 'In_Progress')

        manager = VaultManager(temp_vault)
        is_valid, missing = manager.validate_structure()
        assert is_valid is False
        assert 'Folder: In_Progress' in missing

    def test_write_and_read_file(self, temp_vault):
        """Test writing and reading files."""
        manager = VaultManager(temp_vault)

        # Write file with metadata
        content = "# Test Content\n\nThis is a test."
        metadata = {'source': 'test', 'status': 'pending'}

        success = manager.write_file('Needs_Action/test.md', content, metadata)
        assert success is True
        assert (temp_vault / 'Needs_Action' / 'test.md').exists()

        # Read file back
        post = manager.read_file('Needs_Action/test.md')
        assert post is not None
        assert 'Test Content' in post.content
        assert post.metadata['source'] == 'test'
        assert post.metadata['status'] == 'pending'

    def test_read_nonexistent_file(self, temp_vault):
        """Test reading a file that doesn't exist."""
        manager = VaultManager(temp_vault)
        post = manager.read_file('Needs_Action/nonexistent.md')
        assert post is None

    def test_list_files(self, temp_vault):
        """Test listing files in a folder."""
        manager = VaultManager(temp_vault)

        # Create some test files
        (temp_vault / 'Needs_Action' / 'task1.md').write_text('# Task 1')
        (temp_vault / 'Needs_Action' / 'task2.md').write_text('# Task 2')
        (temp_vault / 'Needs_Action' / 'other.txt').write_text('Not a task')

        files = manager.list_files('Needs_Action', '*.md')
        assert len(files) == 2
        assert all(f.suffix == '.md' for f in files)

    def test_move_file(self, temp_vault):
        """Test moving files within vault."""
        manager = VaultManager(temp_vault)

        # Create source file
        source = temp_vault / 'Needs_Action' / 'task.md'
        source.write_text('# Task')

        # Move to Done
        success = manager.move_file('Needs_Action/task.md', 'Done/task.md')
        assert success is True
        assert not source.exists()
        assert (temp_vault / 'Done' / 'task.md').exists()

    def test_move_to_done(self, temp_vault):
        """Test move_to_done convenience method."""
        manager = VaultManager(temp_vault)

        # Create task
        task = temp_vault / 'Needs_Action' / 'task.md'
        task.write_text('# Task')

        # Move to done
        success = manager.move_to_done('task.md')
        assert success is True
        assert not task.exists()
        assert (temp_vault / 'Done' / 'task.md').exists()

    def test_file_exists(self, temp_vault):
        """Test file existence check."""
        manager = VaultManager(temp_vault)

        assert manager.file_exists('Dashboard.md') is True
        assert manager.file_exists('nonexistent.md') is False

    def test_get_pending_tasks(self, temp_vault):
        """Test getting pending tasks."""
        manager = VaultManager(temp_vault)

        # Create some tasks
        (temp_vault / 'Needs_Action' / 'task1.md').write_text('# Task 1')
        (temp_vault / 'Needs_Action' / 'task2.md').write_text('# Task 2')

        tasks = manager.get_pending_tasks()
        assert len(tasks) == 2

    def test_get_completed_tasks(self, temp_vault):
        """Test getting completed tasks."""
        manager = VaultManager(temp_vault)

        # Create some completed tasks
        (temp_vault / 'Done' / 'done1.md').write_text('# Done 1')
        (temp_vault / 'Done' / 'done2.md').write_text('# Done 2')

        tasks = manager.get_completed_tasks()
        assert len(tasks) == 2

    def test_get_plans(self, temp_vault):
        """Test getting plans."""
        manager = VaultManager(temp_vault)

        # Create some plans
        (temp_vault / 'Plans' / 'plan1.md').write_text('# Plan 1')

        plans = manager.get_plans()
        assert len(plans) == 1

    # --- Silver Tier tests ---

    def test_move_to_in_progress(self, temp_vault):
        """Test move_to_in_progress moves task from Needs_Action to In_Progress."""
        manager = VaultManager(temp_vault)

        # Create task in Needs_Action
        task = temp_vault / 'Needs_Action' / 'move-task.md'
        task.write_text('---\nstatus: in_progress\n---\n# Move Task\n')

        success = manager.move_to_in_progress('move-task.md')
        assert success is True
        assert not task.exists()
        assert (temp_vault / 'In_Progress' / 'move-task.md').exists()

    def test_move_to_in_progress_nonexistent(self, temp_vault):
        """Test move_to_in_progress returns False for missing file."""
        manager = VaultManager(temp_vault)
        success = manager.move_to_in_progress('ghost.md')
        assert success is False

    def test_move_to_done_from_in_progress(self, temp_vault):
        """Test move_to_done picks up tasks from In_Progress first."""
        manager = VaultManager(temp_vault)

        # Create task in In_Progress
        task = temp_vault / 'In_Progress' / 'done-task.md'
        task.write_text('---\nstatus: done\n---\n# Done Task\n')

        success = manager.move_to_done('done-task.md')
        assert success is True
        assert not task.exists()
        assert (temp_vault / 'Done' / 'done-task.md').exists()

    def test_move_to_done_from_in_progress_has_priority(self, temp_vault):
        """Test that In_Progress is checked before Needs_Action for move_to_done."""
        manager = VaultManager(temp_vault)

        # Create same-named task in both folders
        na_task = temp_vault / 'Needs_Action' / 'dup-task.md'
        ip_task = temp_vault / 'In_Progress' / 'dup-task.md'
        na_task.write_text('# From Needs_Action')
        ip_task.write_text('# From In_Progress')

        success = manager.move_to_done('dup-task.md')
        assert success is True
        # In_Progress version should have moved
        assert not ip_task.exists()
        assert (temp_vault / 'Done' / 'dup-task.md').exists()
        # Needs_Action version should still be there
        assert na_task.exists()

    def test_append_movement_log(self, temp_vault):
        """Test appending a movement log entry to a task file."""
        manager = VaultManager(temp_vault)

        # Create a file to append log to
        task = temp_vault / 'In_Progress' / 'logged-task.md'
        task.write_text('---\nstatus: in_progress\n---\n# Logged Task\n')

        success = manager.append_movement_log(
            'In_Progress/logged-task.md', 'Needs_Action', 'In_Progress')
        assert success is True

        content = task.read_text()
        assert '## Movement Log' in content
        assert 'Needs_Action' in content
        assert 'In_Progress' in content

    def test_append_movement_log_existing_section(self, temp_vault):
        """Test appending to an existing Movement Log section."""
        manager = VaultManager(temp_vault)

        # Create a file that already has a Movement Log section
        task = temp_vault / 'Done' / 'multi-log.md'
        task.write_text(
            '---\nstatus: done\n---\n# Multi Log\n\n'
            '## Movement Log\n\n- 2026-01-01 00:00:00: Moved from `Needs_Action` to `In_Progress`\n'
        )

        success = manager.append_movement_log(
            'Done/multi-log.md', 'In_Progress', 'Done')
        assert success is True

        content = task.read_text()
        assert content.count('## Movement Log') == 1
        assert 'In_Progress' in content
        assert 'Done' in content

    def test_append_movement_log_nonexistent_file(self, temp_vault):
        """Test append_movement_log returns False for nonexistent file."""
        manager = VaultManager(temp_vault)
        success = manager.append_movement_log(
            'In_Progress/ghost.md', 'Needs_Action', 'In_Progress')
        assert success is False

    def test_get_in_progress_tasks(self, temp_vault):
        """Test getting in-progress tasks from In_Progress folder."""
        manager = VaultManager(temp_vault)

        # Initially empty
        tasks = manager.get_in_progress_tasks()
        assert len(tasks) == 0

        # Create some in-progress tasks
        (temp_vault / 'In_Progress' / 'ip1.md').write_text('# IP 1')
        (temp_vault / 'In_Progress' / 'ip2.md').write_text('# IP 2')
        (temp_vault / 'In_Progress' / 'ip3.md').write_text('# IP 3')

        tasks = manager.get_in_progress_tasks()
        assert len(tasks) == 3
        assert all(t.suffix == '.md' for t in tasks)

    def test_required_folders_includes_in_progress(self):
        """Test that REQUIRED_FOLDERS includes In_Progress."""
        assert 'In_Progress' in VaultManager.REQUIRED_FOLDERS
        assert 'Needs_Action' in VaultManager.REQUIRED_FOLDERS
        assert 'Done' in VaultManager.REQUIRED_FOLDERS
        assert 'Plans' in VaultManager.REQUIRED_FOLDERS
