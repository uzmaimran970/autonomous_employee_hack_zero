"""
Pytest fixtures for Silver Tier Foundation tests.

Provides common fixtures for vault setup and teardown.
"""

import pytest
from pathlib import Path
import shutil


@pytest.fixture
def temp_vault(tmp_path):
    """
    Create a temporary vault structure for testing.

    Yields the vault path and cleans up after test.
    """
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()

    # Create required folders (Gold Tier includes Rollback_Archive)
    (vault_path / "Needs_Action").mkdir()
    (vault_path / "In_Progress").mkdir()
    (vault_path / "Done").mkdir()
    (vault_path / "Plans").mkdir()
    (vault_path / "Rollback_Archive").mkdir()

    # Create required files
    (vault_path / "Dashboard.md").write_text("# Dashboard\n\n**Last Updated**: Test\n")
    (vault_path / "Company_Handbook.md").write_text("# Company Handbook\n\nTest rules.\n")
    (vault_path / ".task_hashes").touch()

    yield vault_path

    # Cleanup is automatic with tmp_path


@pytest.fixture
def temp_watch_dir(tmp_path):
    """
    Create a temporary watch directory for testing.

    Yields the directory path.
    """
    watch_dir = tmp_path / "watch_dir"
    watch_dir.mkdir()
    yield watch_dir


@pytest.fixture
def sample_task_content():
    """Sample task content for testing."""
    return """---
source: file_watcher
created: 2026-02-10T12:00:00
original_ref: /path/to/file.txt
status: pending
---

# Task: Test Task

## Content

This is a test task for unit testing.

## Metadata

- **Source**: file_watcher
- **Detected**: 2026-02-10 12:00:00
- **Original Reference**: /path/to/file.txt
"""


@pytest.fixture
def sample_plan_content():
    """Sample plan content for testing."""
    return """---
plan_id: plan-20260210-120000
task_ref: 20260210-120000-test-task.md
generated: 2026-02-10T12:00:00
generator: claude-code
step_count: 3
---

# Plan: Test Task

**Source Task**: [[Needs_Action/20260210-120000-test-task.md]]
**Generated**: 2026-02-10 12:00:00

## Action Steps

- [ ] Step 1: Review the test task
- [ ] Step 2: Execute test actions
- [ ] Step 3: Verify results

## Notes

Test plan for unit testing.
"""
