"""
Unit tests for vault_initializer module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.vault_initializer import (
    create_folders,
    write_dashboard,
    write_handbook,
    create_hash_registry,
    init_vault
)


class TestVaultInitializer:
    """Tests for vault initializer functions."""

    def test_create_folders(self, tmp_path):
        """Test folder creation."""
        vault_path = tmp_path / "test_vault"

        success = create_folders(vault_path)
        assert success is True
        assert vault_path.exists()
        assert (vault_path / "Needs_Action").exists()
        assert (vault_path / "Done").exists()
        assert (vault_path / "Plans").exists()

    def test_create_folders_already_exists(self, tmp_path):
        """Test folder creation when folders already exist."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Needs_Action").mkdir()

        # Should not fail if folders exist
        success = create_folders(vault_path)
        assert success is True

    def test_write_dashboard(self, tmp_path):
        """Test Dashboard.md creation."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        success = write_dashboard(vault_path)
        assert success is True

        dashboard = vault_path / "Dashboard.md"
        assert dashboard.exists()

        content = dashboard.read_text()
        assert "# Dashboard" in content
        assert "Last Updated" in content
        assert "Recent Activity" in content
        assert "Statistics" in content

    def test_write_handbook(self, tmp_path):
        """Test Company_Handbook.md creation."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        success = write_handbook(vault_path)
        assert success is True

        handbook = vault_path / "Company_Handbook.md"
        assert handbook.exists()

        content = handbook.read_text()
        assert "# Company Handbook" in content
        assert "AI Behavior Rules" in content
        assert "Task Processing Guidelines" in content

    def test_create_hash_registry(self, tmp_path):
        """Test hash registry file creation."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        success = create_hash_registry(vault_path)
        assert success is True
        assert (vault_path / ".task_hashes").exists()

    def test_init_vault_full(self, tmp_path):
        """Test full vault initialization."""
        vault_path = tmp_path / "test_vault"

        success = init_vault(vault_path)
        assert success is True

        # Check all components
        assert vault_path.exists()
        assert (vault_path / "Needs_Action").exists()
        assert (vault_path / "Done").exists()
        assert (vault_path / "Plans").exists()
        assert (vault_path / "Dashboard.md").exists()
        assert (vault_path / "Company_Handbook.md").exists()
        assert (vault_path / ".task_hashes").exists()

    def test_init_vault_default_path(self, tmp_path, monkeypatch):
        """Test vault initialization with default path."""
        monkeypatch.chdir(tmp_path)

        success = init_vault()
        assert success is True
        assert (tmp_path / "autonomous_employee").exists()
