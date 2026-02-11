"""
Unit tests for TaskClassifier.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from processors.task_classifier import TaskClassifier


class TestTaskClassifier:
    """Tests for TaskClassifier class."""

    def test_init(self):
        """Test TaskClassifier initialization."""
        classifier = TaskClassifier()
        assert classifier is not None
        assert len(classifier.SIMPLE_OPERATIONS) > 0

    def test_single_step_file_task_is_simple(self):
        """Gate 1: Single-step file operation classifies as simple."""
        classifier = TaskClassifier()
        task_content = "# Create Report\n\nCreate a summary file of today's tasks."
        plan_steps = ["Create file report.md with task summary"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'

    def test_multi_step_is_complex(self):
        """Gate 1: Multi-step task (>5 steps) classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Complex Task\n\nThis requires multiple steps."
        plan_steps = [
            "Step 1: Review the current code",
            "Step 2: Refactor the module",
            "Step 3: Write tests",
            "Step 4: Update documentation",
            "Step 5: Run linting checks",
            "Step 6: Deploy to staging",
        ]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_empty_steps_is_simple(self):
        """Gate 1: No steps (empty list) classifies as simple (0 <= 1)."""
        classifier = TaskClassifier()
        task_content = "# Empty Task"
        plan_steps = []

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'

    def test_single_step_with_header_only_is_simple(self):
        """Gate 1: Steps that are only headers don't count as actionable."""
        classifier = TaskClassifier()
        task_content = "# Simple Task"
        plan_steps = [
            "# Action Steps",
            "Create file output.md",
        ]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'

    def test_credential_reference_is_complex(self):
        """Gate 2: Task with credential reference classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Update Config\n\nUpdate the api_key in the config file."
        plan_steps = ["Update the api_key value in config.yaml"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_password_reference_is_complex(self):
        """Gate 2: Task mentioning password classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Reset Password\n\nReset the admin password."
        plan_steps = ["Change the password in settings"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_token_reference_in_steps_is_complex(self):
        """Gate 2: Plan steps mentioning token classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Update Service Config"
        plan_steps = ["Update the oauth token in the service configuration"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_env_file_reference_is_complex(self):
        """Gate 2: Reference to .env file classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Modify Environment\n\nUpdate .env file."
        plan_steps = ["Edit .env to add new variable"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_non_deterministic_api_call_is_complex(self):
        """Gate 3: Task requiring API call classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Fetch Data\n\nFetch data from external API."
        plan_steps = ["Make an api call to the weather service"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_non_deterministic_download_is_complex(self):
        """Gate 3: Task requiring download classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Download Report"
        plan_steps = ["Download the quarterly report from the server"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_non_deterministic_database_is_complex(self):
        """Gate 3: Task involving database classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Update Records"
        plan_steps = ["Update the database with new records"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_non_deterministic_deploy_is_complex(self):
        """Gate 3: Task involving deployment classifies as complex."""
        classifier = TaskClassifier()
        task_content = "# Deploy Service"
        plan_steps = ["Deploy the updated service to production"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_deterministic_file_operation_is_simple(self):
        """Gate 3: Pure file operation with no non-deterministic keywords is simple."""
        classifier = TaskClassifier()
        task_content = "# Create Notes\n\nCreate a notes file."
        plan_steps = ["Create file notes.md with meeting notes"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'

    def test_all_three_gates_pass(self):
        """All three gates pass for a single-step, no-credential, deterministic file task."""
        classifier = TaskClassifier()
        task_content = "# Copy Document\n\nCopy the document to the archive."
        plan_steps = ["Copy file document.md to archive folder"]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'

    def test_gate_1_fails_first(self):
        """Gate 1 (step count) is checked first; >5 steps = complex regardless of content."""
        classifier = TaskClassifier()
        task_content = "# Simple File Task"
        plan_steps = [
            "Create file output.md",
            "Move file to Done folder",
            "Create file summary.md",
            "Copy file to archive",
            "Create file index.md",
            "Move file to backup",
        ]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'complex'

    def test_whitespace_only_steps_ignored(self):
        """Steps that are only whitespace are not counted as actionable."""
        classifier = TaskClassifier()
        task_content = "# Task"
        plan_steps = [
            "   ",
            "",
            "Create file report.md",
        ]

        result = classifier.classify(task_content, plan_steps)
        assert result == 'simple'
