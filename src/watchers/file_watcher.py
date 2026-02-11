"""
File System Watcher for Bronze Tier Foundation.

Monitors a directory for new files and creates tasks in /Needs_Action.
Uses the watchdog library for cross-platform file system events.
"""

import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import frontmatter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from watchers.base_watcher import BaseWatcher
from utils.hash_registry import HashRegistry
from utils.vault_manager import VaultManager

logger = logging.getLogger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Handles file system events for the FileWatcher.

    Only processes file creation events, ignoring directories
    and other event types.
    """

    def __init__(self, watcher: 'FileWatcher'):
        """
        Initialize the event handler.

        Args:
            watcher: Parent FileWatcher instance.
        """
        super().__init__()
        self.watcher = watcher

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Handle file creation events.

        Args:
            event: The file creation event.
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info(f"New file detected: {file_path}")

        # Create task from the new file
        self.watcher.create_task_from_file(file_path)


class FileWatcher(BaseWatcher):
    """
    Watches a directory for new files and creates tasks.

    When a new file is added to the monitored directory,
    creates a corresponding task in /Needs_Action.
    """

    SOURCE_TYPE = 'file_watcher'

    def __init__(self, vault_path: Path, watch_dir: Path):
        """
        Initialize the FileWatcher.

        Args:
            vault_path: Path to the Obsidian vault root.
            watch_dir: Directory to monitor for new files.
        """
        super().__init__(vault_path)
        self.watch_dir = Path(watch_dir)
        self.vault_manager = VaultManager(vault_path)
        self.hash_registry = HashRegistry(vault_path)
        self.observer: Optional[Observer] = None

    def watch(self) -> None:
        """
        Start watching the directory for new files.

        Blocks until stop() is called or interrupted.
        """
        if not self.watch_dir.exists():
            logger.error(f"Watch directory does not exist: {self.watch_dir}")
            raise FileNotFoundError(f"Watch directory not found: {self.watch_dir}")

        logger.info(f"Starting file watcher on: {self.watch_dir}")
        print(f"📁 Watching directory: {self.watch_dir}")
        print(f"📂 Tasks will be saved to: {self.needs_action_path}")
        print("Press Ctrl+C to stop...")

        event_handler = FileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        self.is_running = True

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("File watcher interrupted by user")
        finally:
            self.stop()

    def start_watching(self) -> None:
        """
        Start watching in non-blocking mode.

        Use stop() to stop the watcher later.
        """
        if not self.watch_dir.exists():
            logger.error(f"Watch directory does not exist: {self.watch_dir}")
            raise FileNotFoundError(f"Watch directory not found: {self.watch_dir}")

        logger.info(f"Starting file watcher (non-blocking) on: {self.watch_dir}")

        event_handler = FileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        self.is_running = True

    def stop_watching(self) -> None:
        """Alias for stop() method."""
        self.stop()

    def stop(self) -> None:
        """Stop watching the directory."""
        self.is_running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")

    def create_task(self, title: str, content: str,
                    source: str, original_ref: str,
                    file_type: str = 'unknown') -> Optional[Path]:
        """
        Create a task file in the Needs_Action folder.

        Args:
            title: Task title
            content: Task content
            source: Source type
            original_ref: Reference to original file
            file_type: File type category

        Returns:
            Path to created task file, or None if failed.
        """
        filename = self.generate_task_filename(title)
        body, metadata = self.format_task_content(
            title, content, source, original_ref, file_type=file_type)

        task_path = self.needs_action_path / filename

        try:
            post = frontmatter.Post(body, **metadata)
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))

            logger.info(f"Created task: {task_path}")
            print(f"✅ Created task: {filename}")
            return task_path
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def create_task_from_file(self, file_path: Path) -> Optional[Path]:
        """
        Create a task from a detected file.

        Includes deduplication check to prevent duplicate tasks.

        Args:
            file_path: Path to the detected file.

        Returns:
            Path to created task file, or None if skipped/failed.
        """
        # Compute content hash for deduplication
        content_hash = self.hash_registry.compute_file_hash(file_path)

        # Check for duplicates
        if self.hash_registry.has_hash(content_hash):
            logger.info(f"Duplicate file detected, skipping: {file_path}")
            print(f"⏭️  Skipping duplicate: {file_path.name}")
            return None

        # Generate task content
        title = file_path.name
        try:
            # Try to read file content for the task
            if file_path.suffix.lower() in ['.txt', '.md', '.csv', '.json', '.log']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read(2000)  # First 2KB
                content = f"New file detected: **{file_path.name}**\n\n```\n{file_content}\n```"
            else:
                # For binary files, just include metadata
                stat = file_path.stat()
                content = f"""New file detected: **{file_path.name}**

- **Size**: {stat.st_size:,} bytes
- **Type**: {file_path.suffix or 'Unknown'}
- **Modified**: {datetime.fromtimestamp(stat.st_mtime).isoformat()}
"""
        except Exception as e:
            logger.error(f"Error reading file content: {e}")
            content = f"New file detected: **{file_path.name}**"

        # Detect file type
        file_type = self.detect_file_type(file_path)

        # Create the task
        task_path = self.create_task(
            title=title,
            content=content,
            source=self.SOURCE_TYPE,
            original_ref=str(file_path),
            file_type=file_type
        )

        # Add hash to registry if task was created successfully
        if task_path:
            self.hash_registry.add_hash(content_hash)

        return task_path


if __name__ == "__main__":
    # Allow running directly for testing
    import sys
    from utils.config import load_config

    config = load_config()
    watcher = FileWatcher(
        vault_path=config['vault_path'],
        watch_dir=config['watch_dir']
    )
    watcher.watch()
