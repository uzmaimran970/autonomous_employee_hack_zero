"""
Pytest fixtures for Silver Tier Foundation tests.

Provides common fixtures for vault setup and teardown.
Platinum Tier adds Learning_Data folder and intelligence module fixtures.
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

    # Create required folders (Gold Tier includes Rollback_Archive, Platinum adds Learning_Data)
    (vault_path / "Needs_Action").mkdir()
    (vault_path / "In_Progress").mkdir()
    (vault_path / "Done").mkdir()
    (vault_path / "Plans").mkdir()
    (vault_path / "Rollback_Archive").mkdir()
    (vault_path / "Learning_Data").mkdir()

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


# ── Platinum Tier Fixtures ──────────────────────────────────────


@pytest.fixture
def platinum_config():
    """Default Platinum Tier configuration for testing."""
    return {
        'vault_path': Path('/tmp/test_vault'),
        'prediction_threshold': 0.7,
        'max_parallel_tasks': 3,
        'learning_window_days': 30,
        'max_recovery_attempts': 3,
        'task_timeout_minutes': 15,
        'enable_predictive_sla': True,
        'enable_self_healing': True,
        'enable_risk_scoring': True,
        'risk_weight_sla': 0.3,
        'risk_weight_complexity': 0.2,
        'risk_weight_impact': 0.3,
        'risk_weight_failure': 0.2,
        'sla_simple_minutes': 2,
        'sla_complex_minutes': 10,
        'operations_log_path': Path('/tmp/test_ops.log'),
    }


@pytest.fixture
def make_execution_graph():
    """Factory fixture for creating ExecutionGraphs."""
    from intelligence.execution_graph import ExecutionGraph, ExecutionStep

    def _make(task_id="test_task.md", step_count=3, with_alternatives=False):
        steps = []
        for i in range(step_count):
            alt = f"step_{i}_alt" if with_alternatives and i > 0 else None
            step = ExecutionStep(
                step_id=f"step_{i}",
                name=f"Step {i}: action {i}",
                priority=i + 1,
                estimated_duration=1.0,
                alternative_step=alt,
            )
            steps.append(step)

        # Add alternative steps if requested
        if with_alternatives:
            for i in range(1, step_count):
                steps.append(ExecutionStep(
                    step_id=f"step_{i}_alt",
                    name=f"Alternative for step {i}",
                    priority=i + 1,
                    estimated_duration=1.0,
                ))

        # Sequential edges
        edges = {}
        for i in range(step_count - 1):
            edges[f"step_{i}"] = [f"step_{i + 1}"]

        return ExecutionGraph(
            task_id=task_id, steps=steps, edges=edges,
        )

    return _make


@pytest.fixture
def make_recovery_attempt():
    """Factory fixture for creating RecoveryAttempt records."""
    from intelligence.self_healing import RecoveryAttempt

    def _make(task_id="test_task.md", step_id="step_0",
              attempt_number=1, strategy="retry",
              outcome="success", duration_ms=100.0):
        return RecoveryAttempt(
            task_id=task_id, step_id=step_id,
            attempt_number=attempt_number, strategy=strategy,
            outcome=outcome, duration_ms=duration_ms,
        )

    return _make


@pytest.fixture
def make_risk_score():
    """Factory fixture for creating RiskScore objects."""
    from intelligence.risk_engine import RiskScore

    def _make(task_id="test_task.md", sla_risk=0.5,
              complexity=0.33, impact=0.5, failure_rate=0.0):
        composite = sla_risk * 0.3 + complexity * 0.2 + impact * 0.3 + failure_rate * 0.2
        return RiskScore(
            task_id=task_id, sla_risk=sla_risk,
            complexity=complexity, impact=impact,
            failure_rate=failure_rate, composite_score=composite,
        )

    return _make
