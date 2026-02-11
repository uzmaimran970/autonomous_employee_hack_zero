"""
Hash Registry for Bronze Tier Foundation.

Manages content hashes for task deduplication.
Prevents creating duplicate tasks for the same email/file.
"""

import hashlib
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class HashRegistry:
    """
    Manages a registry of content hashes for deduplication.

    Hashes are stored in a hidden .task_hashes file in the vault root.
    Each line contains one MD5 hash (32 hex characters).
    """

    def __init__(self, vault_path: Path):
        """
        Initialize the hash registry.

        Args:
            vault_path: Path to the vault root directory.
        """
        self.vault_path = Path(vault_path)
        self.hash_file = self.vault_path / '.task_hashes'
        self._hashes: Set[str] = set()
        self._load_hashes()

    def _load_hashes(self) -> None:
        """Load existing hashes from the registry file."""
        if not self.hash_file.exists():
            logger.debug("Hash registry file not found, starting fresh")
            return

        try:
            with open(self.hash_file, 'r', encoding='utf-8') as f:
                for line in f:
                    hash_value = line.strip()
                    if len(hash_value) == 32:  # Valid MD5 hash
                        self._hashes.add(hash_value)
            logger.info(f"Loaded {len(self._hashes)} hashes from registry")
        except Exception as e:
            logger.error(f"Error loading hash registry: {e}")

    def add_hash(self, content_hash: str) -> bool:
        """
        Add a hash to the registry.

        Args:
            content_hash: MD5 hash string (32 characters)

        Returns:
            True if added successfully, False if already exists or error.
        """
        if len(content_hash) != 32:
            logger.error(f"Invalid hash length: {len(content_hash)}")
            return False

        if content_hash in self._hashes:
            logger.debug(f"Hash already exists: {content_hash[:8]}...")
            return False

        try:
            # Append to file
            with open(self.hash_file, 'a', encoding='utf-8') as f:
                f.write(content_hash + '\n')

            # Add to in-memory set
            self._hashes.add(content_hash)
            logger.debug(f"Added hash: {content_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error adding hash to registry: {e}")
            return False

    def has_hash(self, content_hash: str) -> bool:
        """
        Check if a hash exists in the registry.

        Args:
            content_hash: MD5 hash string to check.

        Returns:
            True if hash exists, False otherwise.
        """
        return content_hash in self._hashes

    def load_hashes(self) -> Set[str]:
        """
        Reload and return all hashes from the registry.

        Returns:
            Set of all hash strings.
        """
        self._load_hashes()
        return self._hashes.copy()

    def clear(self) -> bool:
        """
        Clear all hashes from the registry.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self._hashes.clear()
            if self.hash_file.exists():
                self.hash_file.unlink()
            self.hash_file.touch()
            logger.info("Cleared hash registry")
            return True
        except Exception as e:
            logger.error(f"Error clearing hash registry: {e}")
            return False

    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute MD5 hash of content.

        Args:
            content: String content to hash.

        Returns:
            32-character hexadecimal MD5 hash.
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_file_hash(file_path: Path, max_bytes: int = 1024) -> str:
        """
        Compute hash for a file (path + first N bytes of content).

        Args:
            file_path: Path to the file.
            max_bytes: Maximum bytes to read (default 1KB).

        Returns:
            32-character hexadecimal MD5 hash.
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read(max_bytes)
            # Include path in hash to differentiate files with same content
            hash_input = str(file_path) + content.decode('utf-8', errors='ignore')
            return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Error computing file hash: {e}")
            # Fall back to path-only hash
            return hashlib.md5(str(file_path).encode('utf-8')).hexdigest()

    def __len__(self) -> int:
        """Return number of hashes in registry."""
        return len(self._hashes)

    def __contains__(self, item: str) -> bool:
        """Check if hash is in registry."""
        return self.has_hash(item)
