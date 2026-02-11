"""
Rollback Manager for Gold Tier Foundation.

Creates pre-execution snapshots of task files and outputs,
restores them on failure, and purges expired snapshots.
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from utils.operations_logger import OperationsLogger

logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Manages rollback snapshots in /Rollback_Archive/.

    Snapshot structure:
        /Rollback_Archive/{timestamp}-{task_stem}/
            manifest.json
            task.md (copy of original task file)
            outputs/ (copies of any output files)
    """

    def __init__(self, vault_path: Path,
                 ops_logger: Optional[OperationsLogger] = None,
                 retention_days: int = 7):
        """
        Initialize RollbackManager.

        Args:
            vault_path: Path to the vault root.
            ops_logger: Optional OperationsLogger for audit trail.
            retention_days: Days to retain snapshots before purging.
        """
        self.vault_path = Path(vault_path)
        self.archive_path = self.vault_path / 'Rollback_Archive'
        self.ops_logger = ops_logger
        self.retention_days = retention_days

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, task_path: Path) -> Optional[Path]:
        """
        Create a pre-execution snapshot of the task file.

        Copies the task file (and any existing outputs in In_Progress
        matching the task stem) to a timestamped snapshot directory.

        Args:
            task_path: Path to the task file.

        Returns:
            Path to the snapshot directory, or None on failure.
        """
        if not task_path.exists():
            logger.error(f"Cannot create snapshot: task not found: {task_path}")
            return None

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        snapshot_name = f"{timestamp}-{task_path.stem}"
        snapshot_dir = self.archive_path / snapshot_name

        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Copy the task file
            shutil.copy2(str(task_path), str(snapshot_dir / 'task.md'))

            # Copy any existing output files for this task
            outputs_dir = snapshot_dir / 'outputs'
            in_progress = self.vault_path / 'In_Progress'
            copied_outputs = []
            if in_progress.exists():
                for output_file in in_progress.glob(f"*{task_path.stem}*"):
                    if output_file != task_path:
                        outputs_dir.mkdir(exist_ok=True)
                        shutil.copy2(str(output_file), str(outputs_dir / output_file.name))
                        copied_outputs.append(output_file.name)

            # Write manifest
            manifest = {
                'timestamp': datetime.now().isoformat(),
                'task_ref': task_path.name,
                'task_stem': task_path.stem,
                'snapshot_path': str(snapshot_dir),
                'file_list': ['task.md'] + [f'outputs/{f}' for f in copied_outputs],
            }
            manifest_path = snapshot_dir / 'manifest.json'
            manifest_path.write_text(
                json.dumps(manifest, indent=2), encoding='utf-8'
            )

            logger.info(f"Snapshot created: {snapshot_dir}")

            if self.ops_logger:
                self.ops_logger.log(
                    op='rollback_triggered',
                    file=task_path.name,
                    src='In_Progress',
                    dst=str(snapshot_dir),
                    outcome='success',
                    detail=f'snapshot:{snapshot_name}'
                )

            return snapshot_dir

        except Exception as e:
            logger.error(f"Failed to create snapshot for {task_path.name}: {e}")
            if self.ops_logger:
                self.ops_logger.log(
                    op='rollback_triggered',
                    file=task_path.name,
                    src='In_Progress',
                    outcome='failed',
                    detail=f'error:{e}'
                )
            return None

    def restore_snapshot(self, snapshot_dir: Path, task_path: Path) -> bool:
        """
        Restore files from a snapshot directory.

        Copies the task file back and restores any output files.
        Sets task status to 'failed_rollback' via frontmatter update.

        Args:
            snapshot_dir: Path to the snapshot directory.
            task_path: Path where the task file should be restored.

        Returns:
            True if restoration succeeded, False otherwise.
        """
        if not snapshot_dir.exists():
            logger.error(f"Snapshot directory not found: {snapshot_dir}")
            return False

        manifest_path = snapshot_dir / 'manifest.json'
        if not manifest_path.exists():
            logger.error(f"Manifest not found in snapshot: {snapshot_dir}")
            return False

        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

            # Restore the task file
            snapshot_task = snapshot_dir / 'task.md'
            if snapshot_task.exists():
                shutil.copy2(str(snapshot_task), str(task_path))
                logger.info(f"Restored task file: {task_path}")

            # Restore output files
            outputs_dir = snapshot_dir / 'outputs'
            if outputs_dir.exists():
                in_progress = self.vault_path / 'In_Progress'
                for output_file in outputs_dir.iterdir():
                    dest = in_progress / output_file.name
                    shutil.copy2(str(output_file), str(dest))
                    logger.info(f"Restored output: {dest}")

            # Update task status to failed_rollback
            import frontmatter as fm
            if task_path.exists():
                with open(task_path, 'r', encoding='utf-8') as f:
                    post = fm.load(f)
                post.metadata['status'] = 'failed_rollback'
                post.metadata['updated'] = datetime.now().isoformat()
                post.metadata['version'] = post.metadata.get('version', 1) + 1
                with open(task_path, 'w', encoding='utf-8') as f:
                    f.write(fm.dumps(post))

            logger.info(f"Snapshot restored: {snapshot_dir}")

            if self.ops_logger:
                self.ops_logger.log(
                    op='rollback_restored',
                    file=manifest.get('task_ref', 'unknown'),
                    src=str(snapshot_dir),
                    dst='In_Progress',
                    outcome='success',
                    detail=f'restored_files:{len(manifest.get("file_list", []))}'
                )

            return True

        except Exception as e:
            logger.error(f"Failed to restore snapshot {snapshot_dir}: {e}")
            if self.ops_logger:
                self.ops_logger.log(
                    op='rollback_restored',
                    file='unknown',
                    src=str(snapshot_dir),
                    outcome='failed',
                    detail=f'error:{e}'
                )
            return False

    def purge_expired(self) -> int:
        """
        Delete snapshots older than retention_days.

        Returns:
            Number of snapshots purged.
        """
        if not self.archive_path.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        purged = 0

        for snapshot_dir in self.archive_path.iterdir():
            if not snapshot_dir.is_dir():
                continue

            manifest_path = snapshot_dir / 'manifest.json'
            try:
                if manifest_path.exists():
                    manifest = json.loads(
                        manifest_path.read_text(encoding='utf-8')
                    )
                    ts = datetime.fromisoformat(manifest['timestamp'])
                else:
                    # Parse timestamp from directory name (YYYYMMDD-HHMMSS-...)
                    dir_name = snapshot_dir.name
                    ts_str = dir_name[:15]  # YYYYMMDD-HHMMSS
                    ts = datetime.strptime(ts_str, '%Y%m%d-%H%M%S')

                if ts < cutoff:
                    shutil.rmtree(str(snapshot_dir))
                    logger.info(f"Purged expired snapshot: {snapshot_dir.name}")
                    purged += 1

            except Exception as e:
                logger.warning(f"Error checking snapshot {snapshot_dir.name}: {e}")

        if purged > 0:
            logger.info(f"Purged {purged} expired snapshot(s)")

        return purged
