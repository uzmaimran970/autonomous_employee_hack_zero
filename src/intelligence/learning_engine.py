"""
Learning & Optimization Engine for Platinum Tier (P5).

Tracks execution metrics per task type and provides historical
insights to improve planning, risk scoring, and SLA prediction.
"""

import json
import logging
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LearningMetrics:
    """Aggregated historical execution data per task type."""

    task_type: str
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    duration_variance: float = 0.0
    retry_success_count: int = 0
    retry_total_count: int = 0
    sla_breach_count: int = 0
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

    @property
    def failure_rate(self) -> float:
        return self.failure_count / self.total_count if self.total_count > 0 else 0.0

    @property
    def retry_success_rate(self) -> float:
        return self.retry_success_count / self.retry_total_count if self.retry_total_count > 0 else 0.0

    @property
    def sla_compliance_rate(self) -> float:
        return 1.0 - (self.sla_breach_count / self.total_count) if self.total_count > 0 else 1.0

    @property
    def duration_stdev(self) -> float:
        return math.sqrt(self.duration_variance) if self.duration_variance > 0 else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["failure_rate"] = self.failure_rate
        d["retry_success_rate"] = self.retry_success_rate
        d["sla_compliance_rate"] = self.sla_compliance_rate
        d["duration_stdev"] = self.duration_stdev
        return d


class LearningEngine:
    """
    Persists and queries execution metrics per task type.

    Data stored in /Learning_Data/ as:
    - <task_type>.jsonl — individual execution records (JSON Lines)
    - <task_type>.meta.json — aggregated LearningMetrics
    """

    def __init__(self, vault_path: Path, config: dict, ops_logger=None):
        self.learning_dir = Path(vault_path) / "Learning_Data"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.retention_days = config.get("learning_window_days", 30)
        self.ops_logger = ops_logger

    def record(self, task_result: dict) -> bool:
        """
        Persist execution outcome and update aggregates.

        Args:
            task_result: Dict with task_type, duration_ms, outcome (success/failed),
                         retry_count, sla_breached (bool).

        Returns:
            True if recorded successfully.
        """
        task_type = task_result.get("task_type", "general")
        record = {
            "ts": datetime.now().isoformat(),
            "task_type": task_type,
            "duration_ms": task_result.get("duration_ms", 0),
            "outcome": task_result.get("outcome", "success"),
            "retry_count": task_result.get("retry_count", 0),
            "retry_succeeded": task_result.get("retry_succeeded", False),
            "sla_breached": task_result.get("sla_breached", False),
        }

        try:
            # Append raw record
            jsonl_path = self.learning_dir / f"{task_type}.jsonl"
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Update aggregates
            self._update_aggregates(task_type, record)

            # Log
            self._log_update(task_type)
            return True
        except Exception as e:
            logger.error(f"Failed to record learning data: {e}")
            return False

    def query(self, task_type: str) -> Optional[LearningMetrics]:
        """
        Retrieve aggregated metrics for a task type.

        Returns:
            LearningMetrics or None if no data exists.
        """
        meta_path = self.learning_dir / f"{task_type}.meta.json"
        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return LearningMetrics(**{k: v for k, v in data.items()
                                     if k in LearningMetrics.__dataclass_fields__})
        except Exception as e:
            logger.error(f"Failed to read learning data for {task_type}: {e}")
            return None

    def maintenance(self):
        """Purge records older than retention window and recompute aggregates."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for jsonl_path in self.learning_dir.glob("*.jsonl"):
            task_type = jsonl_path.stem
            try:
                lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
                kept = []
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        ts = datetime.fromisoformat(record["ts"])
                        if ts >= cutoff:
                            kept.append(line)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

                jsonl_path.write_text("\n".join(kept) + "\n" if kept else "",
                                     encoding="utf-8")

                # Recompute aggregates from remaining data
                self._recompute_aggregates(task_type, kept)
            except Exception as e:
                logger.error(f"Maintenance error for {task_type}: {e}")

    def _update_aggregates(self, task_type: str, record: dict):
        """Incrementally update aggregates using Welford's algorithm."""
        metrics = self.query(task_type) or LearningMetrics(task_type=task_type)

        n = metrics.total_count + 1
        duration = record.get("duration_ms", 0)

        # Welford's online algorithm for mean and variance
        old_mean = metrics.avg_duration_ms
        new_mean = old_mean + (duration - old_mean) / n
        new_variance = (
            metrics.duration_variance * (n - 1) + (duration - old_mean) * (duration - new_mean)
        ) / n if n > 1 else 0.0

        metrics.total_count = n
        metrics.avg_duration_ms = new_mean
        metrics.duration_variance = new_variance

        if record.get("outcome") == "success":
            metrics.success_count += 1
        else:
            metrics.failure_count += 1

        if record.get("retry_count", 0) > 0:
            metrics.retry_total_count += 1
            if record.get("retry_succeeded", False):
                metrics.retry_success_count += 1

        if record.get("sla_breached", False):
            metrics.sla_breach_count += 1

        metrics.last_updated = datetime.now().isoformat()

        # Write aggregates
        meta_path = self.learning_dir / f"{task_type}.meta.json"
        meta_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

    def _recompute_aggregates(self, task_type: str, lines: list):
        """Recompute aggregates from raw records after purge."""
        metrics = LearningMetrics(task_type=task_type)

        durations = []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                duration = record.get("duration_ms", 0)
                durations.append(duration)
                metrics.total_count += 1
                if record.get("outcome") == "success":
                    metrics.success_count += 1
                else:
                    metrics.failure_count += 1
                if record.get("retry_count", 0) > 0:
                    metrics.retry_total_count += 1
                    if record.get("retry_succeeded", False):
                        metrics.retry_success_count += 1
                if record.get("sla_breached", False):
                    metrics.sla_breach_count += 1
            except (json.JSONDecodeError, KeyError):
                continue

        if durations:
            mean = sum(durations) / len(durations)
            metrics.avg_duration_ms = mean
            if len(durations) > 1:
                metrics.duration_variance = sum((d - mean) ** 2 for d in durations) / len(durations)

        metrics.last_updated = datetime.now().isoformat()
        meta_path = self.learning_dir / f"{task_type}.meta.json"
        meta_path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")

    def _log_update(self, task_type: str):
        """Log learning_update event."""
        if not self.ops_logger:
            return
        metrics = self.query(task_type)
        count = metrics.total_count if metrics else 0
        self.ops_logger.log(
            op="learning_update", file=task_type, src="learning_engine",
            outcome="success", detail=f"task_type={task_type} total_count={count}",
        )
