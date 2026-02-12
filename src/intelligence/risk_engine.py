"""
Dynamic Risk-Based Prioritization Engine for Platinum Tier (P4).

Computes composite risk scores for pending tasks and reorders
execution by risk score instead of Gold's static priority ordering.
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

COMPLEXITY_MAP = {"simple": 0.33, "complex": 0.67, "manual_review": 1.0}
IMPACT_MAP = {"low": 0.25, "normal": 0.50, "high": 0.75, "critical": 1.0}


@dataclass
class RiskScore:
    """Composite risk score for dynamic task prioritization."""

    task_id: str
    sla_risk: float
    complexity: float
    impact: float
    failure_rate: float
    composite_score: float
    computed_at: str = ""

    def __post_init__(self):
        if not self.computed_at:
            self.computed_at = datetime.now().isoformat()
        for name, val in [("sla_risk", self.sla_risk), ("complexity", self.complexity),
                          ("impact", self.impact), ("failure_rate", self.failure_rate),
                          ("composite_score", self.composite_score)]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {val}")

    def to_dict(self) -> dict:
        return asdict(self)


class RiskEngine:
    """
    Computes composite risk scores and reorders task execution.

    Formula: risk_score = (sla_risk * w1) + (complexity * w2) +
             (impact * w3) + (failure_rate * w4)
    """

    def __init__(self, config: dict, ops_logger=None):
        self.config = config
        self.w_sla = config.get("risk_weight_sla", 0.3)
        self.w_complexity = config.get("risk_weight_complexity", 0.2)
        self.w_impact = config.get("risk_weight_impact", 0.3)
        self.w_failure = config.get("risk_weight_failure", 0.2)
        self.ops_logger = ops_logger

    def compute_score(self, task_id: str, task_metadata: dict,
                      historical_data: Optional[dict] = None) -> RiskScore:
        """
        Compute composite risk score for a task.

        Args:
            task_id: Task filename.
            task_metadata: Dict with 'classification', 'priority', 'sla_risk'.
            historical_data: Dict with 'failure_rate' from learning engine.

        Returns:
            RiskScore with all components and composite score.
        """
        classification = task_metadata.get("classification", "simple")
        priority = task_metadata.get("priority", "normal")
        sla_risk = float(task_metadata.get("sla_risk", 0.0))

        complexity = COMPLEXITY_MAP.get(classification, 0.33)
        impact = IMPACT_MAP.get(priority, 0.50)
        failure_rate = 0.0
        if historical_data:
            failure_rate = float(historical_data.get("failure_rate", 0.0))

        composite = (
            sla_risk * self.w_sla +
            complexity * self.w_complexity +
            impact * self.w_impact +
            failure_rate * self.w_failure
        )
        composite = max(0.0, min(1.0, composite))

        score = RiskScore(
            task_id=task_id,
            sla_risk=sla_risk,
            complexity=complexity,
            impact=impact,
            failure_rate=failure_rate,
            composite_score=composite,
        )

        self._log_score(score)
        return score

    def reorder_tasks(self, tasks_with_metadata: list,
                      historical_data_map: Optional[dict] = None) -> list:
        """
        Reorder tasks by composite risk score (highest first).

        Args:
            tasks_with_metadata: List of (task_id, metadata) tuples.
            historical_data_map: Dict of task_type -> historical data.

        Returns:
            List of (task_id, metadata, RiskScore) tuples sorted by risk score descending.
        """
        scored = []
        for task_id, metadata in tasks_with_metadata:
            task_type = metadata.get("type", "general")
            hist = {}
            if historical_data_map:
                hist = historical_data_map.get(task_type, {})
            try:
                score = self.compute_score(task_id, metadata, hist)
                scored.append((task_id, metadata, score))
            except Exception as e:
                logger.warning(f"Failed to compute risk score for {task_id}: {e}")
                # Use zero score — will sort to end (Gold fallback ordering)
                fallback = RiskScore(
                    task_id=task_id, sla_risk=0.0, complexity=0.33,
                    impact=0.5, failure_rate=0.0, composite_score=0.0,
                )
                scored.append((task_id, metadata, fallback))

        # Sort by composite_score descending (highest risk first)
        scored.sort(key=lambda x: x[2].composite_score, reverse=True)

        # Log priority adjustments
        self._log_reorder(scored)

        return scored

    def _log_score(self, score):
        """Log risk score computation."""
        if not self.ops_logger:
            return
        detail = (
            f"sla={score.sla_risk:.2f} complexity={score.complexity:.2f} "
            f"impact={score.impact:.2f} failure={score.failure_rate:.2f} "
            f"composite={score.composite_score:.3f}"
        )
        self.ops_logger.log(
            op="risk_scored", file=score.task_id, src="risk_engine",
            outcome="success", detail=detail,
        )

    def _log_reorder(self, scored_tasks):
        """Log priority adjustments when order changes."""
        if not self.ops_logger or not scored_tasks:
            return
        order = [t[0] for t in scored_tasks]
        detail = f"execution_order={order[:5]} total={len(scored_tasks)}"
        self.ops_logger.log(
            op="priority_adjusted", file=order[0] if order else "none",
            src="risk_engine", outcome="success", detail=detail,
        )
