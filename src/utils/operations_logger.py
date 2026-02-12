"""
Operations Logger for Silver Tier Foundation.

Append-only JSON Lines logger for all task operations.
Stored outside the Obsidian vault to prevent watcher detection.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class OperationsLogger:
    """
    Append-only operations log using JSON Lines format.

    Each entry records: timestamp, operation type, file, source,
    destination, outcome, and detail.
    """

    VALID_OPS = {
        'task_created', 'task_moved', 'plan_generated',
        'task_classified', 'task_executed', 'credential_flagged', 'error',
        # Gold Tier operations
        'step_executed', 'sla_breach', 'rollback_triggered',
        'rollback_restored', 'gate_blocked', 'override_applied',
        'notification_sent', 'notification_failed', 'heartbeat_fail',
        # Platinum Tier operations
        'sla_prediction', 'risk_scored', 'self_heal_retry',
        'self_heal_alternative', 'self_heal_partial', 'learning_update',
        'priority_adjusted', 'concurrency_queued',
    }
    VALID_OUTCOMES = {'success', 'failed', 'flagged'}

    def __init__(self, log_path: Path):
        """
        Initialize OperationsLogger.

        Args:
            log_path: Path to the operations log file (outside vault).
        """
        self.log_path = Path(log_path)
        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, op: str, file: str, src: str,
            dst: Optional[str] = None, outcome: str = 'success',
            detail: str = '') -> bool:
        """
        Append a log entry.

        Args:
            op: Operation type (task_created, task_moved, etc.)
            file: Task or plan filename.
            src: Source folder or 'external'.
            dst: Destination folder or None.
            outcome: Result (success, failed, flagged).
            detail: Additional context.

        Returns:
            True if entry written successfully.
        """
        entry = {
            'ts': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.') +
                  f'{datetime.now().microsecond // 1000:03d}',
            'op': op,
            'file': file,
            'src': src,
            'dst': dst if dst else 'null',
            'outcome': outcome,
            'detail': detail,
        }

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to write operations log: {e}")
            return False

    def read_recent(self, n: int = 50) -> List[dict]:
        """
        Read the most recent N log entries.

        Args:
            n: Number of entries to return (default: 50).

        Returns:
            List of log entry dicts, newest first.
        """
        if not self.log_path.exists():
            return []

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            entries = []
            for line in lines[-n:]:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

            entries.reverse()
            return entries
        except Exception as e:
            logger.error(f"Failed to read operations log: {e}")
            return []

    def count_errors(self, hours: int = 24) -> int:
        """
        Count error entries within the last N hours.

        Args:
            hours: Time window in hours (default: 24).

        Returns:
            Number of error entries.
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)
        count = 0

        if not self.log_path.exists():
            return 0

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get('outcome') == 'failed':
                        try:
                            ts = datetime.fromisoformat(
                                entry['ts'].replace('.', ':', 2)
                                if entry['ts'].count('.') > 1
                                else entry['ts']
                            )
                            if ts.timestamp() >= cutoff:
                                count += 1
                        except (ValueError, KeyError):
                            count += 1  # Count if we can't parse timestamp
        except Exception as e:
            logger.error(f"Failed to count errors: {e}")

        return count

    def get_errors(self, n: int = 5) -> List[dict]:
        """
        Get the most recent N error entries.

        Args:
            n: Number of error entries to return (default: 5).

        Returns:
            List of error entry dicts, newest first.
        """
        if not self.log_path.exists():
            return []

        errors = []
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get('outcome') == 'failed':
                        errors.append(entry)

            errors.reverse()
            return errors[:n]
        except Exception as e:
            logger.error(f"Failed to get errors: {e}")
            return []
