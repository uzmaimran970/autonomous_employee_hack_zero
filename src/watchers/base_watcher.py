"""
Base Watcher for Bronze Tier Foundation.

Abstract base class defining the interface for all watchers.
Watchers monitor external sources (files, email) and create tasks.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


FILE_TYPE_MAP = {
    # Documents
    '.txt': 'document', '.md': 'document', '.doc': 'document',
    '.docx': 'document', '.pdf': 'document', '.rtf': 'document',
    '.odt': 'document',
    # Images
    '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
    '.gif': 'image', '.bmp': 'image', '.svg': 'image',
    '.webp': 'image',
    # Data
    '.csv': 'data', '.json': 'data', '.xml': 'data',
    '.xlsx': 'data', '.xls': 'data', '.tsv': 'data',
    '.yaml': 'data', '.yml': 'data',
    # Email
    '.eml': 'email', '.msg': 'email',
}


class BaseWatcher(ABC):
    """
    Abstract base class for watchers.

    Watchers are responsible for:
    1. Monitoring an external source for new items
    2. Converting detected items to task markdown files
    3. Saving tasks to the /Needs_Action folder
    """

    def __init__(self, vault_path: Path):
        """
        Initialize the watcher.

        Args:
            vault_path: Path to the Obsidian vault root directory.
        """
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.is_running = False

    @abstractmethod
    def watch(self) -> None:
        """
        Start watching for new items.

        This method should run continuously until stop() is called.
        Implementations should handle their own event loop or polling.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop watching for new items.

        This method should gracefully stop the watcher and clean up
        any resources (threads, connections, etc.).
        """
        pass

    @staticmethod
    def detect_file_type(file_path: Path) -> str:
        """
        Detect file type category from extension.

        Args:
            file_path: Path to the file.

        Returns:
            Type category string (document, image, data, email, unknown).
        """
        ext = Path(file_path).suffix.lower()
        return FILE_TYPE_MAP.get(ext, 'unknown')

    @abstractmethod
    def create_task(self, title: str, content: str,
                    source: str, original_ref: str,
                    file_type: str = 'unknown') -> Optional[Path]:
        """
        Create a task file in the Needs_Action folder.

        Args:
            title: Task title (used in filename and heading)
            content: Main content/body of the task
            source: Source type ('gmail', 'file_watcher', etc.)
            original_ref: Reference to original item (email ID, file path)

        Returns:
            Path to created task file, or None if failed.
        """
        pass

    def generate_task_filename(self, title: str) -> str:
        """
        Generate a unique filename for a task.

        Format: {YYYYMMDD}-{HHMMSS}-{slug}.md

        Args:
            title: Task title to slugify

        Returns:
            Generated filename string.
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        # Create slug from title: lowercase, replace spaces with hyphens
        slug = title.lower().replace(' ', '-')
        # Remove non-alphanumeric characters except hyphens
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        # Truncate to 30 characters
        slug = slug[:30].rstrip('-')
        return f"{timestamp}-{slug}.md"

    def format_task_content(self, title: str, content: str,
                            source: str, original_ref: str,
                            file_type: str = 'unknown') -> tuple[str, dict]:
        """
        Format task content with YAML frontmatter and markdown body.

        Args:
            title: Task title
            content: Main content
            source: Source type
            original_ref: Reference to original item
            file_type: File type category (document, image, data, email, unknown)

        Returns:
            Tuple of (markdown_body, frontmatter_dict)
        """
        now = datetime.now()

        fm = {
            'source': source,
            'type': file_type,
            'created': now.isoformat(),
            'original_ref': str(original_ref),
            'status': 'pending',
            'version': 1,
            'priority': 'normal',
        }

        body = f"""# Task: {title}

## Content

{content}

## Metadata

- **Source**: {source}
- **Type**: {file_type}
- **Detected**: {now.strftime('%Y-%m-%d %H:%M:%S')}
- **Original Reference**: {original_ref}
"""

        return body, fm
