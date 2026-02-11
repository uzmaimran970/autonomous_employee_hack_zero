"""
Vault Manager for Bronze Tier Foundation.

Provides read/write operations for the Obsidian vault structure.
All task and plan files are stored as Markdown with YAML frontmatter.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import yaml
import frontmatter

logger = logging.getLogger(__name__)


class VaultManager:
    """
    Manages read/write operations for the Obsidian vault.

    The vault structure:
    - /Needs_Action: Pending tasks from watchers
    - /In_Progress: Tasks currently being processed
    - /Done: Completed tasks
    - /Plans: Generated action plans
    - Dashboard.md: Activity summary
    - Company_Handbook.md: AI behavior rules
    """

    REQUIRED_FOLDERS = ['Needs_Action', 'In_Progress', 'Done', 'Plans', 'Rollback_Archive']
    REQUIRED_FILES = ['Dashboard.md', 'Company_Handbook.md']

    def __init__(self, vault_path: Path):
        """
        Initialize VaultManager with vault path.

        Args:
            vault_path: Path to the Obsidian vault root directory.
        """
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.in_progress_path = self.vault_path / 'In_Progress'
        self.done_path = self.vault_path / 'Done'
        self.plans_path = self.vault_path / 'Plans'
        self.rollback_archive_path = self.vault_path / 'Rollback_Archive'

    def validate_structure(self) -> tuple[bool, List[str]]:
        """
        Validate the vault has required folder structure.

        Returns:
            Tuple of (is_valid, list_of_missing_items)
        """
        missing = []

        if not self.vault_path.exists():
            missing.append(f"Vault root: {self.vault_path}")
            return False, missing

        for folder in self.REQUIRED_FOLDERS:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                missing.append(f"Folder: {folder}")

        for file in self.REQUIRED_FILES:
            file_path = self.vault_path / file
            if not file_path.exists():
                missing.append(f"File: {file}")

        return len(missing) == 0, missing

    def read_file(self, relative_path: str) -> Optional[frontmatter.Post]:
        """
        Read a markdown file with YAML frontmatter.

        Args:
            relative_path: Path relative to vault root.

        Returns:
            frontmatter.Post object with content and metadata, or None if not found.
        """
        file_path = self.vault_path / relative_path
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return frontmatter.load(f)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def write_file(self, relative_path: str, content: str,
                   metadata: Optional[dict] = None) -> bool:
        """
        Write a markdown file with optional YAML frontmatter.

        Args:
            relative_path: Path relative to vault root.
            content: Markdown content body.
            metadata: Optional YAML frontmatter dictionary.

        Returns:
            True if successful, False otherwise.
        """
        file_path = self.vault_path / relative_path

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if metadata:
                post = frontmatter.Post(content, **metadata)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            logger.info(f"Written file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    def list_files(self, folder: str, pattern: str = "*.md") -> List[Path]:
        """
        List files in a vault folder matching pattern.

        Args:
            folder: Folder name (e.g., 'Needs_Action', 'Plans')
            pattern: Glob pattern for files (default: *.md)

        Returns:
            List of Path objects for matching files.
        """
        folder_path = self.vault_path / folder
        if not folder_path.exists():
            logger.warning(f"Folder not found: {folder_path}")
            return []

        return sorted(folder_path.glob(pattern))

    def move_file(self, source_relative: str, dest_relative: str) -> bool:
        """
        Move a file within the vault.

        Args:
            source_relative: Source path relative to vault root.
            dest_relative: Destination path relative to vault root.

        Returns:
            True if successful, False otherwise.
        """
        source_path = self.vault_path / source_relative
        dest_path = self.vault_path / dest_relative

        if not source_path.exists():
            logger.error(f"Source file not found: {source_path}")
            return False

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(source_path), str(dest_path))
            logger.info(f"Moved file: {source_path} -> {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False

    def move_to_in_progress(self, task_filename: str) -> bool:
        """
        Move a task from Needs_Action to In_Progress.

        Appends a movement log entry to the task file.

        Args:
            task_filename: Name of the task file.

        Returns:
            True if successful, False otherwise.
        """
        source = f"Needs_Action/{task_filename}"
        dest = f"In_Progress/{task_filename}"
        if self.move_file(source, dest):
            self.append_movement_log(dest, 'Needs_Action', 'In_Progress')
            return True
        return False

    def move_to_done(self, task_filename: str) -> bool:
        """
        Move a task from Needs_Action or In_Progress to Done.

        Checks In_Progress first, then Needs_Action.
        Appends a movement log entry to the task file.

        Args:
            task_filename: Name of the task file.

        Returns:
            True if successful, False otherwise.
        """
        # Try from In_Progress first
        in_progress_path = f"In_Progress/{task_filename}"
        if self.file_exists(in_progress_path):
            if self.move_file(in_progress_path, f"Done/{task_filename}"):
                self.append_movement_log(
                    f"Done/{task_filename}", 'In_Progress', 'Done')
                return True
            return False

        # Fallback to Needs_Action (Bronze compatibility)
        source = f"Needs_Action/{task_filename}"
        dest = f"Done/{task_filename}"
        if self.move_file(source, dest):
            self.append_movement_log(dest, 'Needs_Action', 'Done')
            return True
        return False

    def update_task_status(self, task_path: str, new_status: str) -> bool:
        """
        Update the status field in a task's YAML frontmatter.

        Args:
            task_path: Path to task file relative to vault root.
            new_status: New status value ('pending' or 'done')

        Returns:
            True if successful, False otherwise.
        """
        post = self.read_file(task_path)
        if post is None:
            return False

        post.metadata['status'] = new_status
        post.metadata['updated'] = datetime.now().isoformat()

        file_path = self.vault_path / task_path
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            logger.info(f"Updated task status to '{new_status}': {task_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False

    def get_pending_tasks(self) -> List[Path]:
        """Get all pending task files from Needs_Action folder."""
        return self.list_files('Needs_Action')

    def get_in_progress_tasks(self) -> List[Path]:
        """Get all in-progress task files from In_Progress folder."""
        return self.list_files('In_Progress')

    def get_completed_tasks(self) -> List[Path]:
        """Get all completed task files from Done folder."""
        return self.list_files('Done')

    def get_plans(self) -> List[Path]:
        """Get all plan files from Plans folder."""
        return self.list_files('Plans')

    def append_movement_log(self, file_path: str, source: str,
                            destination: str) -> bool:
        """
        Append a movement log entry to a task file.

        Adds a ## Movement Log section (or appends to existing one)
        with a timestamped entry recording the folder transition.

        Args:
            file_path: Path to the task file relative to vault root.
            source: Source folder name.
            destination: Destination folder name.

        Returns:
            True if successful, False otherwise.
        """
        full_path = self.vault_path / file_path
        if not full_path.exists():
            logger.error(f"File not found for movement log: {full_path}")
            return False

        try:
            content = full_path.read_text(encoding='utf-8')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"- {timestamp}: Moved from `{source}` to `{destination}`"

            if '## Movement Log' in content:
                content = content.replace(
                    '## Movement Log\n',
                    f'## Movement Log\n\n{log_entry}\n'
                )
            else:
                content += f"\n\n## Movement Log\n\n{log_entry}\n"

            full_path.write_text(content, encoding='utf-8')
            logger.info(f"Appended movement log: {source} -> {destination} for {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error appending movement log: {e}")
            return False

    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in the vault."""
        return (self.vault_path / relative_path).exists()
