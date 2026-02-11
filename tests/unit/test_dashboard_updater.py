"""
Unit tests for DashboardUpdater.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.dashboard_updater import DashboardUpdater, DASHBOARD_TEMPLATE
from utils.operations_logger import OperationsLogger


class TestDashboardUpdater:
    """Tests for DashboardUpdater class."""

    def test_init(self, temp_vault):
        """Test DashboardUpdater initialization."""
        updater = DashboardUpdater(temp_vault)
        assert updater.vault_path == temp_vault
        assert updater.dashboard_path == temp_vault / "Dashboard.md"

    def test_count_pending_tasks(self, temp_vault):
        """Test counting pending tasks."""
        updater = DashboardUpdater(temp_vault)

        # Initially empty
        assert updater.count_pending_tasks() == 0

        # Add some tasks
        (temp_vault / "Needs_Action" / "task1.md").write_text("# Task 1")
        (temp_vault / "Needs_Action" / "task2.md").write_text("# Task 2")

        assert updater.count_pending_tasks() == 2

    def test_count_completed_tasks(self, temp_vault):
        """Test counting completed tasks."""
        updater = DashboardUpdater(temp_vault)

        assert updater.count_completed_tasks() == 0

        (temp_vault / "Done" / "done1.md").write_text("# Done 1")
        assert updater.count_completed_tasks() == 1

    def test_count_plans(self, temp_vault):
        """Test counting plans."""
        updater = DashboardUpdater(temp_vault)

        assert updater.count_plans() == 0

        (temp_vault / "Plans" / "plan1.md").write_text("# Plan 1")
        assert updater.count_plans() == 1

    def test_add_activity_entry(self, temp_vault):
        """Test adding activity entries."""
        updater = DashboardUpdater(temp_vault)

        updater.add_activity_entry("Test activity")
        assert len(updater._activity_log) == 1
        assert "Test activity" in updater._activity_log[0]

    def test_activity_entry_limit(self, temp_vault):
        """Test activity log respects max entries."""
        updater = DashboardUpdater(temp_vault)

        # Add more than max entries
        for i in range(15):
            updater.add_activity_entry(f"Activity {i}")

        assert len(updater._activity_log) == DashboardUpdater.MAX_ACTIVITY_ENTRIES

    def test_get_activity_log_empty(self, temp_vault):
        """Test activity log when empty."""
        updater = DashboardUpdater(temp_vault)
        log = updater.get_activity_log()
        assert "No recent activity" in log

    def test_get_activity_log_with_entries(self, temp_vault):
        """Test activity log formatting."""
        updater = DashboardUpdater(temp_vault)

        updater.add_activity_entry("Activity 1")
        updater.add_activity_entry("Activity 2")

        log = updater.get_activity_log()
        assert "Activity 1" in log
        assert "Activity 2" in log
        assert log.startswith("-")

    def test_get_watcher_status(self, temp_vault):
        """Test watcher status formatting."""
        updater = DashboardUpdater(temp_vault)

        status = updater.get_watcher_status(
            file_watcher_running=True,
            gmail_configured=False
        )

        assert "File Watcher" in status
        assert "Running" in status
        assert "Gmail Watcher" in status
        assert "Not configured" in status

    def test_refresh_dashboard(self, temp_vault):
        """Test dashboard refresh."""
        updater = DashboardUpdater(temp_vault)

        # Add some data
        (temp_vault / "Needs_Action" / "task.md").write_text("# Task")
        (temp_vault / "Plans" / "plan.md").write_text("# Plan")
        updater.add_activity_entry("Test activity")

        success = updater.refresh_dashboard()
        assert success is True

        # Check dashboard content
        content = (temp_vault / "Dashboard.md").read_text()
        assert "# Dashboard" in content
        assert "Pending Tasks" in content
        assert "Test activity" in content

    def test_update_with_activity(self, temp_vault):
        """Test update method with activity message."""
        updater = DashboardUpdater(temp_vault)

        success = updater.update("New activity")
        assert success is True

        content = (temp_vault / "Dashboard.md").read_text()
        assert "New activity" in content

    def test_log_task_created(self, temp_vault):
        """Test logging task creation."""
        updater = DashboardUpdater(temp_vault)

        updater.log_task_created("test-task.md")
        assert any("Task created" in entry for entry in updater._activity_log)

    def test_log_plan_generated(self, temp_vault):
        """Test logging plan generation."""
        updater = DashboardUpdater(temp_vault)

        updater.log_plan_generated("test-plan.md")
        assert any("Plan generated" in entry for entry in updater._activity_log)

    def test_log_task_completed(self, temp_vault):
        """Test logging task completion."""
        updater = DashboardUpdater(temp_vault)

        updater.log_task_completed("test-task.md")
        assert any("Task completed" in entry for entry in updater._activity_log)

    # --- Silver Tier tests ---

    def test_count_in_progress_tasks(self, temp_vault):
        """Test counting in-progress tasks."""
        updater = DashboardUpdater(temp_vault)

        # Initially empty
        assert updater.count_in_progress_tasks() == 0

        # Add some in-progress tasks
        (temp_vault / "In_Progress" / "ip1.md").write_text("# IP 1")
        (temp_vault / "In_Progress" / "ip2.md").write_text("# IP 2")

        assert updater.count_in_progress_tasks() == 2

    def test_calculate_avg_completion_time_no_tasks(self, temp_vault):
        """Test avg completion time returns N/A when no tasks."""
        updater = DashboardUpdater(temp_vault)
        result = updater.calculate_avg_completion_time()
        assert result == "N/A"

    def test_calculate_avg_completion_time_with_tasks(self, temp_vault):
        """Test avg completion time calculation from frontmatter."""
        import frontmatter as fm

        updater = DashboardUpdater(temp_vault)

        # Create completed tasks with created/updated timestamps
        task1 = temp_vault / "Done" / "timed1.md"
        post1 = fm.Post(
            "# Timed Task 1",
            created="2026-02-10T10:00:00",
            updated="2026-02-10T10:05:00",
            status="done"
        )
        with open(task1, 'w', encoding='utf-8') as f:
            f.write(fm.dumps(post1))

        task2 = temp_vault / "Done" / "timed2.md"
        post2 = fm.Post(
            "# Timed Task 2",
            created="2026-02-10T10:00:00",
            updated="2026-02-10T10:10:00",
            status="done"
        )
        with open(task2, 'w', encoding='utf-8') as f:
            f.write(fm.dumps(post2))

        result = updater.calculate_avg_completion_time()
        # Average of 5m and 10m = 7.5m
        assert result != "N/A"
        # Should be in minutes format
        assert 'm' in result or 's' in result

    def test_calculate_avg_completion_time_missing_timestamps(self, temp_vault):
        """Test avg completion time handles tasks without created/updated."""
        updater = DashboardUpdater(temp_vault)

        # Create a task without timestamps
        task = temp_vault / "Done" / "notimed.md"
        task.write_text("---\nstatus: done\n---\n# No Timestamps\n")

        result = updater.calculate_avg_completion_time()
        assert result == "N/A"

    def test_calculate_error_rate_no_logger(self, temp_vault):
        """Test error rate returns N/A when no logger configured."""
        updater = DashboardUpdater(temp_vault)
        result = updater.calculate_error_rate()
        assert "N/A" in result

    def test_calculate_error_rate_with_logger(self, temp_vault, tmp_path):
        """Test error rate calculation with OperationsLogger."""
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)

        # Log some entries including errors
        ops_logger.log(op='task_created', file='ok.md', src='watcher', outcome='success')
        ops_logger.log(op='error', file='bad.md', src='executor', outcome='failed',
                       detail='Test error')
        ops_logger.log(op='error', file='bad2.md', src='executor', outcome='failed',
                       detail='Another error')

        updater = DashboardUpdater(temp_vault, ops_logger=ops_logger)
        result = updater.calculate_error_rate()
        assert "2 error(s)" in result
        assert "24h" in result

    def test_get_recent_errors_no_logger(self, temp_vault):
        """Test recent errors message when no logger configured."""
        updater = DashboardUpdater(temp_vault)
        result = updater.get_recent_errors()
        assert "No error logger configured" in result

    def test_get_recent_errors_no_errors(self, temp_vault, tmp_path):
        """Test recent errors when logger has no errors."""
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)
        ops_logger.log(op='task_created', file='ok.md', src='watcher', outcome='success')

        updater = DashboardUpdater(temp_vault, ops_logger=ops_logger)
        result = updater.get_recent_errors()
        assert "No recent errors" in result

    def test_get_recent_errors_with_errors(self, temp_vault, tmp_path):
        """Test recent errors formatting with actual errors."""
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)
        ops_logger.log(op='error', file='fail.md', src='executor', outcome='failed',
                       detail='Something went wrong')

        updater = DashboardUpdater(temp_vault, ops_logger=ops_logger)
        result = updater.get_recent_errors()
        assert "fail.md" in result
        assert "Something went wrong" in result

    def test_silver_template_rendering(self, temp_vault, tmp_path):
        """Test that Silver template renders with In-Progress, Avg Completion Time, Error Rate."""
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)

        updater = DashboardUpdater(temp_vault, ops_logger=ops_logger)

        # Add some in-progress tasks
        (temp_vault / "In_Progress" / "task-ip.md").write_text("# IP Task")

        success = updater.refresh_dashboard()
        assert success is True

        content = (temp_vault / "Dashboard.md").read_text()

        # Silver Tier specific fields
        assert "In-Progress" in content
        assert "Average Completion Time" in content
        assert "Error Rate" in content
        assert "Recent Errors" in content
        assert "Metrics" in content

    def test_silver_template_has_in_progress_count(self, temp_vault, tmp_path):
        """Test that refreshed dashboard shows correct in-progress count."""
        log_path = tmp_path / "ops.jsonl"
        ops_logger = OperationsLogger(log_path)

        updater = DashboardUpdater(temp_vault, ops_logger=ops_logger)

        (temp_vault / "In_Progress" / "ip1.md").write_text("# IP 1")
        (temp_vault / "In_Progress" / "ip2.md").write_text("# IP 2")
        (temp_vault / "In_Progress" / "ip3.md").write_text("# IP 3")

        updater.refresh_dashboard()
        content = (temp_vault / "Dashboard.md").read_text()

        # Check that in-progress count is 3
        assert "**In-Progress Tasks**: 3" in content
