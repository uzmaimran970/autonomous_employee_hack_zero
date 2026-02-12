"""
Safe Concurrency Control for Platinum Tier (P6).

Enforces configurable maximum parallel execution limit,
queues excess tasks by risk score, and prevents deadlocks.
"""

import logging
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencySlot:
    """Tracks an active concurrent execution slot."""

    slot_id: int
    task_id: str
    started_at: str = ""
    timeout_at: str = ""
    status: str = "active"

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        valid_statuses = {"active", "completed", "timed_out", "released"}
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")

    def to_dict(self) -> dict:
        return asdict(self)


class ConcurrencyController:
    """
    Semaphore-based concurrency control with risk-score-based queuing.

    Enforces MAX_PARALLEL_TASKS limit and per-task timeouts.
    """

    def __init__(self, config: dict, ops_logger=None):
        self.config = config
        self.max_parallel = config.get("max_parallel_tasks", 3)
        self.timeout_minutes = config.get("task_timeout_minutes", 15)
        self.ops_logger = ops_logger

        self._semaphore = threading.Semaphore(self.max_parallel)
        self._lock = threading.Lock()
        self._active_slots: dict = {}  # slot_id -> ConcurrencySlot
        self._queue: list = []  # (risk_score, task_id) sorted by risk descending
        self._next_slot_id = 0

    def acquire(self, task_id: str) -> Optional[ConcurrencySlot]:
        """
        Attempt to acquire an execution slot.

        Args:
            task_id: Task filename requesting execution.

        Returns:
            ConcurrencySlot if acquired, None if limit reached.
        """
        acquired = self._semaphore.acquire(blocking=False)
        if not acquired:
            return None

        with self._lock:
            slot_id = self._next_slot_id
            self._next_slot_id += 1

            timeout_at = (
                datetime.now() + timedelta(minutes=self.timeout_minutes)
            ).isoformat()

            slot = ConcurrencySlot(
                slot_id=slot_id,
                task_id=task_id,
                timeout_at=timeout_at,
            )
            self._active_slots[slot_id] = slot

        return slot

    def release(self, slot_id: int):
        """
        Release an execution slot.

        Args:
            slot_id: The slot to release.
        """
        with self._lock:
            if slot_id in self._active_slots:
                slot = self._active_slots.pop(slot_id)
                slot.status = "released"

        self._semaphore.release()

    def complete(self, slot_id: int):
        """Mark a slot as completed and release it."""
        with self._lock:
            if slot_id in self._active_slots:
                self._active_slots[slot_id].status = "completed"

        self.release(slot_id)

    def queue(self, task_id: str, risk_score: float = 0.0):
        """
        Add a task to the queue ordered by risk score.

        Args:
            task_id: Task filename to queue.
            risk_score: Composite risk score for ordering.
        """
        with self._lock:
            self._queue.append((risk_score, task_id))
            self._queue.sort(key=lambda x: x[0], reverse=True)

        if self.ops_logger:
            self.ops_logger.log(
                op="concurrency_queued", file=task_id,
                src="concurrency_controller", outcome="success",
                detail=f"risk_score={risk_score:.3f} queue_position={self._get_queue_position(task_id)}",
            )

    def dequeue(self) -> Optional[str]:
        """Remove and return the highest-risk task from the queue."""
        with self._lock:
            if self._queue:
                _, task_id = self._queue.pop(0)
                return task_id
        return None

    def get_active_count(self) -> int:
        """Return the number of currently active slots."""
        with self._lock:
            return len(self._active_slots)

    def get_queued(self) -> list:
        """Return queued tasks in risk-score order."""
        with self._lock:
            return [(tid, score) for score, tid in self._queue]

    def check_timeouts(self) -> list:
        """
        Check for timed-out slots and release them.

        Returns:
            List of task_ids that timed out.
        """
        now = datetime.now()
        timed_out = []

        with self._lock:
            for slot_id, slot in list(self._active_slots.items()):
                try:
                    timeout = datetime.fromisoformat(slot.timeout_at)
                    if now >= timeout:
                        slot.status = "timed_out"
                        timed_out.append((slot_id, slot.task_id))
                except (ValueError, TypeError):
                    continue

        for slot_id, task_id in timed_out:
            self.release(slot_id)
            logger.warning(f"Task {task_id} timed out in slot {slot_id}")

        return [tid for _, tid in timed_out]

    def _get_queue_position(self, task_id: str) -> int:
        """Get 1-based position of task in queue."""
        for i, (_, tid) in enumerate(self._queue):
            if tid == task_id:
                return i + 1
        return -1
