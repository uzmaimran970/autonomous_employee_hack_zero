"""
Unit tests for TaskExecutor.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from processors.task_executor import TaskExecutor


class TestTaskExecutor:
    """Tests for TaskExecutor class."""

    def test_init(self, temp_vault):
        """Test TaskExecutor initialization."""
        executor = TaskExecutor(temp_vault)
        assert executor.vault_path == temp_vault

    def test_execute_file_create(self, temp_vault):
        """Test execute() with a file_create step."""
        executor = TaskExecutor(temp_vault)

        # Create a source task file
        task_path = temp_vault / 'In_Progress' / 'source-task.md'
        task_path.write_text('# Source Task\n\nThis is the source task.')

        plan_steps = ["Create a new file with the task summary"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is True
        assert result['operation'] == 'file_create'
        assert 'Created' in result['step_results'][0]['detail']

    def test_execute_summarize(self, temp_vault):
        """Test execute() with a summarize step."""
        executor = TaskExecutor(temp_vault)

        # Create a source task file with content
        task_path = temp_vault / 'In_Progress' / 'summarize-task.md'
        task_path.write_text(
            '# Task: Generate Summary\n\n'
            '- **Source**: file_watcher\n'
            '- **Priority**: high\n\n'
            '## Content\n\nSome detailed task content here.\n'
        )

        plan_steps = ["Create summary of the task content"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is True
        assert result['operation'] == 'summarize'
        assert 'Summarized' in result['step_results'][0]['detail']

    def test_execute_file_copy(self, temp_vault):
        """Test execute() with a file_copy step."""
        executor = TaskExecutor(temp_vault)

        # Create a source task file
        task_path = temp_vault / 'In_Progress' / 'copy-source.md'
        task_path.write_text('# Copy Source\n\nOriginal content.')

        plan_steps = ["Copy file to backup location"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is True
        assert result['operation'] == 'file_copy'
        assert 'Copied' in result['step_results'][0]['detail']

    def test_execute_no_plan_steps(self, temp_vault):
        """Test execute() with empty plan steps."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'empty-task.md'
        task_path.write_text('# Empty Task')

        result = executor.execute(task_path, [])
        assert result['success'] is False
        assert 'No actionable steps' in result['detail']

    def test_execute_no_actionable_step(self, temp_vault):
        """Test execute() with only non-actionable steps (headers)."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'header-task.md'
        task_path.write_text('# Header Task')

        plan_steps = ["# This is just a header", "# Another header"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is False
        assert 'No actionable steps' in result['detail']

    def test_execute_unknown_operation(self, temp_vault):
        """Test execute() with an unrecognized operation."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'unknown-task.md'
        task_path.write_text('# Unknown Task')

        plan_steps = ["Send notification to the team about the update"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is False
        assert result['step_results'][0]['operation'] == 'unknown'
        assert 'not in allowlist' in result['detail']

    def test_execute_file_create_produces_output_file(self, temp_vault):
        """Test that file_create actually creates an output file on disk."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'create-output.md'
        task_path.write_text('# Create Output Task')

        plan_steps = ["Create a new file documenting the results"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is True

        # Check that an output file was created in In_Progress
        output_files = list((temp_vault / 'In_Progress').glob('output-*.md'))
        assert len(output_files) >= 1

    def test_execute_summarize_produces_summary_file(self, temp_vault):
        """Test that summarize creates a summary file on disk."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'sum-task.md'
        task_path.write_text(
            '# Summary Source\n\n- **Key**: Value\n\nContent here.\n'
        )

        plan_steps = ["Generate summary of the task"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is True

        summary_files = list((temp_vault / 'In_Progress').glob('summary-*.md'))
        assert len(summary_files) >= 1

    def test_execute_file_copy_nonexistent_source(self, temp_vault):
        """Test file_copy with a source file that does not exist."""
        executor = TaskExecutor(temp_vault)

        # Use a path that does not exist
        task_path = temp_vault / 'In_Progress' / 'nonexistent-copy.md'

        plan_steps = ["Copy file to archive"]

        result = executor.execute(task_path, plan_steps)
        assert result['success'] is False
        assert 'not found' in result['detail']

    def test_execute_returns_dict_with_expected_keys(self, temp_vault):
        """Test that execute() always returns dict with success, operation, detail."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'keys-task.md'
        task_path.write_text('# Keys Task')

        result = executor.execute(task_path, ["Do something unusual"])
        assert 'success' in result
        assert 'operation' in result
        assert 'detail' in result

    def test_execute_strips_checkbox_prefix(self, temp_vault):
        """Test that checkbox prefixes are stripped from plan steps."""
        executor = TaskExecutor(temp_vault)

        task_path = temp_vault / 'In_Progress' / 'checkbox-task.md'
        task_path.write_text('# Checkbox Task')

        plan_steps = ["- [ ] Create a new file with results"]

        result = executor.execute(task_path, plan_steps)
        assert result['operation'] == 'file_create'
        assert result['success'] is True
