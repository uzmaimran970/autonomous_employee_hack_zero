"""
SLA Tracker for Gold Tier Foundation.

Tracks task completion times against SLA thresholds,
detects breaches, and computes compliance percentages.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from utils.config import get_config
from utils.operations_logger import OperationsLogger

logger = logging.getLogger(__name__)


class SLATracker:
    """
    Tracks SLA compliance for task execution.

    Compares classified_at → completed_at timestamps against
    configured SLA thresholds (SLA_SIMPLE_MINUTES, SLA_COMPLEX_MINUTES).
    """

    def __init__(self, config: Optional[dict] = None,
                 ops_logger: Optional[OperationsLogger] = None):
        """
        Initialize SLATracker.

        Args:
            config: Config dict with SLA thresholds.
            ops_logger: OperationsLogger for breach logging.
        """
        if config is None:
            config = get_config()
        self.sla_simple_minutes = config.get('sla_simple_minutes', 2)
        self.sla_complex_minutes = config.get('sla_complex_minutes', 10)
        self.ops_logger = ops_logger

    def check_sla(self, task_path: Path) -> dict:
        """
        Check if a completed task met its SLA threshold.

        Reads classified_at and completed_at from frontmatter,
        computes duration, and logs sla_breach if exceeded.

        Args:
            task_path: Path to the task file.

        Returns:
            Dict with 'compliant' (bool), 'duration_minutes' (float),
            'threshold_minutes' (float), 'breach' (bool).
        """
        result = {
            'compliant': True,
            'duration_minutes': 0.0,
            'threshold_minutes': 0.0,
            'breach': False,
        }

        try:
            with open(task_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
        except Exception as e:
            logger.error(f"Cannot read task for SLA check: {e}")
            return result

        classified_at = post.metadata.get('classified_at')
        completed_at = post.metadata.get('completed_at')
        complexity = post.metadata.get('complexity', 'simple')

        if not classified_at or not completed_at:
            logger.debug(f"Missing timestamps for SLA check: {task_path.name}")
            return result

        try:
            start = datetime.fromisoformat(classified_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds() / 60.0
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid timestamps for SLA check: {e}")
            return result

        threshold = (self.sla_simple_minutes if complexity == 'simple'
                     else self.sla_complex_minutes)

        result['duration_minutes'] = round(duration, 2)
        result['threshold_minutes'] = threshold

        if duration > threshold:
            result['compliant'] = False
            result['breach'] = True
            logger.warning(
                f"SLA breach: {task_path.name} took {duration:.1f}min "
                f"(threshold: {threshold}min, complexity: {complexity})"
            )
            if self.ops_logger:
                self.ops_logger.log(
                    op='sla_breach',
                    file=task_path.name,
                    src='sla_tracker',
                    outcome='flagged',
                    detail=(
                        f'duration:{duration:.1f}min '
                        f'threshold:{threshold}min '
                        f'complexity:{complexity}'
                    )
                )
        else:
            logger.info(
                f"SLA compliant: {task_path.name} took {duration:.1f}min "
                f"(threshold: {threshold}min)"
            )

        return result

    def compute_compliance(self, hours: int = 24) -> dict:
        """
        Compute SLA compliance percentage from operations log.

        Args:
            hours: Time window in hours (default: 24).

        Returns:
            Dict with 'total', 'compliant', 'breached', 'compliance_pct'.
        """
        result = {
            'total': 0,
            'compliant': 0,
            'breached': 0,
            'compliance_pct': 100.0,
        }

        if not self.ops_logger:
            return result

        try:
            cutoff = datetime.now().timestamp() - (hours * 3600)
            recent = self.ops_logger.read_recent(500)

            completed = 0
            breached = 0

            for entry in recent:
                try:
                    ts_str = entry.get('ts', '')
                    # Parse the timestamp
                    ts = datetime.fromisoformat(
                        ts_str.replace('.', ':', 2)
                        if ts_str.count('.') > 1 else ts_str
                    )
                    if ts.timestamp() < cutoff:
                        continue
                except (ValueError, TypeError):
                    continue

                if entry.get('op') == 'task_executed':
                    completed += 1
                elif entry.get('op') == 'sla_breach':
                    breached += 1

            result['total'] = completed
            result['breached'] = breached
            result['compliant'] = completed - breached
            if completed > 0:
                result['compliance_pct'] = round(
                    ((completed - breached) / completed) * 100, 1
                )

        except Exception as e:
            logger.error(f"Error computing SLA compliance: {e}")

        return result

    def estimate_duration(self, complexity: str) -> Optional[float]:
        """
        Estimate task duration from historical operations log averages.

        Args:
            complexity: 'simple' or 'complex'.

        Returns:
            Estimated minutes, or None if no historical data.
        """
        if not self.ops_logger:
            return None

        try:
            recent = self.ops_logger.read_recent(200)
            durations = []

            for entry in recent:
                if (entry.get('op') == 'task_executed' and
                        entry.get('outcome') == 'success'):
                    detail = entry.get('detail', '')
                    if f'complexity:{complexity}' in detail:
                        # Default averages based on complexity
                        durations.append(
                            1.0 if complexity == 'simple' else 5.0
                        )

            if durations:
                return round(sum(durations) / len(durations), 2)
        except Exception as e:
            logger.warning(f"Error estimating duration: {e}")

        return None
