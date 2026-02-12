"""
Self-Healing Execution Engine for Platinum Tier (P2).

Implements a recovery cascade before Gold rollback:
1. Retry the failed step (1 attempt)
2. Attempt alternative strategy if defined in execution graph
3. Partial recovery — preserve completed steps, isolate failed step
4. Fall back to Gold rollback mechanism
"""

import time
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAttempt:
    """Record of a single self-healing recovery attempt."""

    task_id: str
    step_id: str
    attempt_number: int
    strategy: str
    outcome: str
    duration_ms: float
    timestamp: str = ""
    error_detail: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        valid_strategies = {"retry", "alternative", "partial"}
        if self.strategy not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}, got {self.strategy}")
        valid_outcomes = {"success", "failed"}
        if self.outcome not in valid_outcomes:
            raise ValueError(f"outcome must be one of {valid_outcomes}, got {self.outcome}")
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms must be non-negative, got {self.duration_ms}")

    def to_dict(self) -> dict:
        return asdict(self)


class SelfHealingEngine:
    """
    Orchestrates self-healing recovery before Gold rollback.

    Recovery cascade: retry -> alternative -> partial -> Gold fallback
    """

    def __init__(self, config: dict, rollback_manager=None, ops_logger=None):
        self.config = config
        self.max_attempts = config.get("max_recovery_attempts", 3)
        self.rollback_manager = rollback_manager
        self.ops_logger = ops_logger

    def recover(self, task_path, failed_step, execution_graph=None, execute_fn=None):
        """
        Attempt recovery for a failed step.

        Args:
            task_path: Path to the task file.
            failed_step: The ExecutionStep that failed.
            execution_graph: The ExecutionGraph (for alternative lookup).
            execute_fn: Callable to re-execute a step (step -> bool).

        Returns:
            List of RecoveryAttempt records for all attempts made.
        """
        task_id = str(task_path)
        attempts = []
        attempt_num = 0

        # Strategy 1: Retry
        if attempt_num < self.max_attempts:
            attempt_num += 1
            attempt = self._attempt_retry(task_id, failed_step, attempt_num, execute_fn)
            attempts.append(attempt)
            self._log_attempt(attempt)
            if attempt.outcome == "success":
                return attempts

        # Strategy 2: Alternative
        if attempt_num < self.max_attempts and execution_graph:
            alt_step = self._find_alternative(failed_step, execution_graph)
            if alt_step:
                attempt_num += 1
                attempt = self._attempt_alternative(
                    task_id, failed_step, alt_step, attempt_num, execute_fn
                )
                attempts.append(attempt)
                self._log_attempt(attempt)
                if attempt.outcome == "success":
                    return attempts

        # Strategy 3: Partial recovery
        if attempt_num < self.max_attempts:
            attempt_num += 1
            attempt = self._attempt_partial(
                task_id, failed_step, attempt_num, execution_graph
            )
            attempts.append(attempt)
            self._log_attempt(attempt)
            if attempt.outcome == "success":
                return attempts

        # All strategies exhausted — Gold rollback will be invoked by caller
        return attempts

    def _attempt_retry(self, task_id, failed_step, attempt_num, execute_fn):
        """Retry the failed step once."""
        start = time.time()
        try:
            if execute_fn and execute_fn(failed_step):
                duration = (time.time() - start) * 1000
                return RecoveryAttempt(
                    task_id=task_id, step_id=failed_step.step_id,
                    attempt_number=attempt_num, strategy="retry",
                    outcome="success", duration_ms=duration,
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return RecoveryAttempt(
                task_id=task_id, step_id=failed_step.step_id,
                attempt_number=attempt_num, strategy="retry",
                outcome="failed", duration_ms=duration,
                error_detail=str(e),
            )

        duration = (time.time() - start) * 1000
        return RecoveryAttempt(
            task_id=task_id, step_id=failed_step.step_id,
            attempt_number=attempt_num, strategy="retry",
            outcome="failed", duration_ms=duration,
        )

    def _find_alternative(self, failed_step, execution_graph):
        """Look up the alternative step in the execution graph."""
        if not failed_step.alternative_step:
            return None
        step_map = {s.step_id: s for s in execution_graph.steps}
        return step_map.get(failed_step.alternative_step)

    def _attempt_alternative(self, task_id, failed_step, alt_step, attempt_num, execute_fn):
        """Execute an alternative step."""
        start = time.time()
        try:
            if execute_fn and execute_fn(alt_step):
                duration = (time.time() - start) * 1000
                return RecoveryAttempt(
                    task_id=task_id, step_id=failed_step.step_id,
                    attempt_number=attempt_num, strategy="alternative",
                    outcome="success", duration_ms=duration,
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return RecoveryAttempt(
                task_id=task_id, step_id=failed_step.step_id,
                attempt_number=attempt_num, strategy="alternative",
                outcome="failed", duration_ms=duration,
                error_detail=str(e),
            )

        duration = (time.time() - start) * 1000
        return RecoveryAttempt(
            task_id=task_id, step_id=failed_step.step_id,
            attempt_number=attempt_num, strategy="alternative",
            outcome="failed", duration_ms=duration,
        )

    def _attempt_partial(self, task_id, failed_step, attempt_num, execution_graph):
        """
        Partial recovery: preserve completed steps, isolate failed step.

        Marks the failed step for manual intervention while keeping
        all completed steps intact.
        """
        start = time.time()
        try:
            if execution_graph:
                completed = [s for s in execution_graph.steps if s.status == "completed"]
                if completed:
                    # Partial recovery succeeds if at least some steps completed
                    failed_step.status = "failed"
                    duration = (time.time() - start) * 1000
                    return RecoveryAttempt(
                        task_id=task_id, step_id=failed_step.step_id,
                        attempt_number=attempt_num, strategy="partial",
                        outcome="success", duration_ms=duration,
                    )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return RecoveryAttempt(
                task_id=task_id, step_id=failed_step.step_id,
                attempt_number=attempt_num, strategy="partial",
                outcome="failed", duration_ms=duration,
                error_detail=str(e),
            )

        duration = (time.time() - start) * 1000
        return RecoveryAttempt(
            task_id=task_id, step_id=failed_step.step_id,
            attempt_number=attempt_num, strategy="partial",
            outcome="failed", duration_ms=duration,
        )

    def _log_attempt(self, attempt):
        """Log a recovery attempt via operations logger."""
        if not self.ops_logger:
            return
        op_map = {
            "retry": "self_heal_retry",
            "alternative": "self_heal_alternative",
            "partial": "self_heal_partial",
        }
        op = op_map.get(attempt.strategy, "self_heal_retry")
        detail = (
            f"strategy={attempt.strategy} outcome={attempt.outcome} "
            f"duration_ms={attempt.duration_ms:.1f}"
        )
        if attempt.error_detail:
            detail += f" error={attempt.error_detail}"
        self.ops_logger.log(
            op=op, file=attempt.task_id, src="self_heal",
            outcome=attempt.outcome, detail=detail,
        )
