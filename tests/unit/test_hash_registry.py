"""
Unit tests for HashRegistry.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.hash_registry import HashRegistry


class TestHashRegistry:
    """Tests for HashRegistry class."""

    def test_init_empty(self, temp_vault):
        """Test initialization with empty registry."""
        registry = HashRegistry(temp_vault)
        assert len(registry) == 0

    def test_compute_hash(self):
        """Test hash computation."""
        hash1 = HashRegistry.compute_hash("test content")
        hash2 = HashRegistry.compute_hash("test content")
        hash3 = HashRegistry.compute_hash("different content")

        assert len(hash1) == 32  # MD5 hex is 32 chars
        assert hash1 == hash2  # Same content = same hash
        assert hash1 != hash3  # Different content = different hash

    def test_add_hash(self, temp_vault):
        """Test adding hashes to registry."""
        registry = HashRegistry(temp_vault)

        test_hash = "a" * 32
        success = registry.add_hash(test_hash)
        assert success is True
        assert len(registry) == 1
        assert test_hash in registry

    def test_add_duplicate_hash(self, temp_vault):
        """Test adding duplicate hash returns False."""
        registry = HashRegistry(temp_vault)

        test_hash = "a" * 32
        registry.add_hash(test_hash)

        # Adding same hash again should return False
        success = registry.add_hash(test_hash)
        assert success is False
        assert len(registry) == 1

    def test_has_hash(self, temp_vault):
        """Test checking if hash exists."""
        registry = HashRegistry(temp_vault)

        test_hash = "a" * 32
        assert registry.has_hash(test_hash) is False

        registry.add_hash(test_hash)
        assert registry.has_hash(test_hash) is True

    def test_contains_operator(self, temp_vault):
        """Test __contains__ operator (in)."""
        registry = HashRegistry(temp_vault)

        test_hash = "a" * 32
        assert test_hash not in registry

        registry.add_hash(test_hash)
        assert test_hash in registry

    def test_persistence(self, temp_vault):
        """Test that hashes persist to file."""
        test_hash = "b" * 32

        # Add hash with first instance
        registry1 = HashRegistry(temp_vault)
        registry1.add_hash(test_hash)

        # Create new instance and verify hash loaded
        registry2 = HashRegistry(temp_vault)
        assert test_hash in registry2

    def test_load_hashes(self, temp_vault):
        """Test load_hashes method."""
        registry = HashRegistry(temp_vault)

        # Add some hashes
        registry.add_hash("a" * 32)
        registry.add_hash("b" * 32)

        # Reload and verify
        hashes = registry.load_hashes()
        assert len(hashes) == 2

    def test_clear(self, temp_vault):
        """Test clearing the registry."""
        registry = HashRegistry(temp_vault)
        registry.add_hash("a" * 32)
        registry.add_hash("b" * 32)

        success = registry.clear()
        assert success is True
        assert len(registry) == 0

    def test_invalid_hash_length(self, temp_vault):
        """Test adding hash with invalid length."""
        registry = HashRegistry(temp_vault)

        success = registry.add_hash("short")
        assert success is False

        success = registry.add_hash("a" * 64)  # Too long
        assert success is False

    def test_compute_file_hash(self, temp_vault):
        """Test computing hash from file."""
        test_file = temp_vault / "test.txt"
        test_file.write_text("Test file content")

        hash1 = HashRegistry.compute_file_hash(test_file)
        hash2 = HashRegistry.compute_file_hash(test_file)

        assert len(hash1) == 32
        assert hash1 == hash2  # Same file = same hash
