"""
Task Mover for Silver Tier Foundation.

Polls vault folders and moves tasks between Needs_Action, In_Progress,
and Done based on status field changes in task frontmatter.
"""

import logging
from pathlib import Path
from typing import Optional

import frontmatter

from utils.vault_manager import VaultManager
from utils.operations_logger import OperationsLogger

logger = logging.getLogger(__name__)


class TaskMover:
    """
    Orchestrates automatic task movement between vault folders.

    Checks task status fields and moves files accordingly:
    - status: 'in_progress' in Needs_Action → move to In_Progress
    - status: 'done' in In_Progress → move to Done
    - status: 'done' in Needs_Action → move to Done (skip In_Progress)
    """

    def __init__(self, vault_manager: VaultManager,
                 ops_logger: Optional[OperationsLogger] = None):
        """
        Initialize TaskMover.

        Args:
            vault_manager: VaultManager instance.
            ops_logger: Optional OperationsLogger for audit trail.
        """
        self.vault_manager = vault_manager
        self.ops_logger = ops_logger

    def check_and_move_tasks(self) -> int:
        """
        Poll all folders and move tasks based on status.

        Returns:
            Number of tasks moved.
        """
        moved = 0

        # Check Needs_Action for tasks that should move
        moved += self._check_needs_action()

        # Check In_Progress for tasks that should move to Done
        moved += self._check_in_progress()

        return moved

    def _check_needs_action(self) -> int:
        """Check Needs_Action folder for tasks to move."""
        moved = 0
        tasks = self.vault_manager.get_pending_tasks()

        for task_path in tasks:
            try:
                post = self.vault_manager.read_file(
                    f"Needs_Action/{task_path.name}")
                if post is None:
                    continue

                status = post.metadata.get('status', 'pending')

                if status == 'in_progress':
                    if self.vault_manager.move_to_in_progress(task_path.name):
                        moved += 1
                        self._log_move(task_path.name,
                                       'Needs_Action', 'In_Progress')
                        logger.info(
                            f"Moved to In_Progress: {task_path.name}")

                elif status == 'done':
                    if self.vault_manager.move_to_done(task_path.name):
                        moved += 1
                        self._log_move(task_path.name,
                                       'Needs_Action', 'Done')
                        logger.info(f"Moved to Done: {task_path.name}")

            except Exception as e:
                logger.error(
                    f"Error checking task {task_path.name}: {e}")
                self._log_error(task_path.name, str(e))

        return moved

    def _check_in_progress(self) -> int:
        """Check In_Progress folder for completed or failed tasks."""
        moved = 0
        tasks = self.vault_manager.get_in_progress_tasks()

        for task_path in tasks:
            try:
                post = self.vault_manager.read_file(
                    f"In_Progress/{task_path.name}")
                if post is None:
                    continue

                status = post.metadata.get('status', 'in_progress')

                if status == 'done':
                    if self.vault_manager.move_to_done(task_path.name):
                        moved += 1
                        self._log_move(task_path.name,
                                       'In_Progress', 'Done')
                        logger.info(f"Moved to Done: {task_path.name}")

                elif status in ('failed', 'failed_rollback', 'blocked'):
                    # Keep failed/blocked tasks in In_Progress for manual review
                    logger.info(
                        f"Task {task_path.name} has status '{status}' — "
                        f"keeping in In_Progress for manual review")

            except Exception as e:
                logger.error(
                    f"Error checking task {task_path.name}: {e}")
                self._log_error(task_path.name, str(e))

        return moved

    def _log_move(self, filename: str, src: str, dst: str) -> None:
        """Log a task movement operation."""
        if self.ops_logger:
            self.ops_logger.log(
                op='task_moved',
                file=filename,
                src=src,
                dst=dst,
                outcome='success'
            )

    def _log_error(self, filename: str, detail: str) -> None:
        """Log a task movement error."""
        if self.ops_logger:
            self.ops_logger.log(
                op='error',
                file=filename,
                src='task_mover',
                outcome='failed',
                detail=detail
            )
