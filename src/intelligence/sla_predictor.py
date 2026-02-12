"""
Predictive SLA Monitoring for Platinum Tier (P3).

Uses historical execution duration data to predict the probability
of SLA breach for in-progress tasks, triggering early warnings.
"""

import math
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SLAPrediction:
    """Predicted SLA breach probability for an in-progress task."""

    task_id: str
    task_type: str
    elapsed_minutes: float
    predicted_duration: float
    sla_threshold: float
    probability: float
    exceeds_threshold: bool
    recommendation: str
    predicted_at: str = ""

    def __post_init__(self):
        if not self.predicted_at:
            self.predicted_at = datetime.now().isoformat()
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError(f"probability must be in [0.0, 1.0], got {self.probability}")
        if self.sla_threshold <= 0:
            raise ValueError(f"sla_threshold must be positive, got {self.sla_threshold}")

    def to_dict(self) -> dict:
        return asdict(self)


def _normal_cdf(x: float) -> float:
    """Approximate the cumulative distribution function of the standard normal."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class SLAPredictor:
    """
    Predicts SLA breach probability using historical duration data.

    Uses normal distribution approximation:
    P(breach) = 1 - CDF((threshold - elapsed) / stdev)
    """

    MIN_DATA_POINTS = 3

    def __init__(self, config: dict, ops_logger=None):
        self.config = config
        self.threshold = config.get("prediction_threshold", 0.7)
        self.ops_logger = ops_logger

    def predict(self, task_id: str, task_type: str, elapsed_minutes: float,
                sla_threshold: float, historical_data: Optional[dict] = None) -> SLAPrediction:
        """
        Predict SLA breach probability for a task.

        Args:
            task_id: Task filename.
            task_type: Task type for historical lookup.
            elapsed_minutes: Time elapsed since task started.
            sla_threshold: SLA threshold in minutes.
            historical_data: Dict with avg_duration_ms, duration_variance, total_count.

        Returns:
            SLAPrediction with breach probability and recommendation.
        """
        if elapsed_minutes >= sla_threshold:
            # Already breached
            return self._make_prediction(
                task_id, task_type, elapsed_minutes, sla_threshold,
                predicted_duration=elapsed_minutes, probability=1.0,
            )

        if (historical_data and
                historical_data.get("total_count", 0) >= self.MIN_DATA_POINTS):
            return self._predict_statistical(
                task_id, task_type, elapsed_minutes, sla_threshold, historical_data
            )

        # Fallback: insufficient data
        return self._predict_fallback(
            task_id, task_type, elapsed_minutes, sla_threshold
        )

    def _predict_statistical(self, task_id, task_type, elapsed, threshold, data):
        """Statistical prediction using normal distribution."""
        avg_ms = data.get("avg_duration_ms", 0)
        variance = data.get("duration_variance", 0)
        avg_minutes = avg_ms / 60000.0  # ms to minutes

        if variance <= 0:
            # Zero variance: deterministic prediction
            probability = 0.0 if avg_minutes < threshold else 1.0
            return self._make_prediction(
                task_id, task_type, elapsed, threshold,
                predicted_duration=avg_minutes, probability=probability,
            )

        stdev_minutes = math.sqrt(variance) / 60000.0  # ms to minutes

        if stdev_minutes == 0:
            probability = 0.0 if avg_minutes < threshold else 1.0
        else:
            remaining = threshold - elapsed
            z = (remaining) / stdev_minutes
            probability = 1.0 - _normal_cdf(z)

        probability = max(0.0, min(1.0, probability))

        return self._make_prediction(
            task_id, task_type, elapsed, threshold,
            predicted_duration=avg_minutes, probability=probability,
        )

    def _predict_fallback(self, task_id, task_type, elapsed, threshold):
        """Fallback prediction when insufficient historical data."""
        # Simple ratio-based estimate
        ratio = elapsed / threshold if threshold > 0 else 0
        probability = max(0.0, min(1.0, ratio))

        return self._make_prediction(
            task_id, task_type, elapsed, threshold,
            predicted_duration=threshold, probability=probability,
        )

    def _make_prediction(self, task_id, task_type, elapsed, threshold,
                         predicted_duration, probability):
        """Create a SLAPrediction with recommendation."""
        if probability < 0.3:
            recommendation = "on_track"
        elif probability <= 0.7:
            recommendation = "monitor"
        else:
            recommendation = "at_risk"

        exceeds = probability > self.threshold

        prediction = SLAPrediction(
            task_id=task_id,
            task_type=task_type,
            elapsed_minutes=elapsed,
            predicted_duration=predicted_duration,
            sla_threshold=threshold,
            probability=probability,
            exceeds_threshold=exceeds,
            recommendation=recommendation,
        )

        self._log_prediction(prediction)
        return prediction

    def _log_prediction(self, prediction):
        """Log prediction via operations logger."""
        if not self.ops_logger:
            return
        detail = (
            f"probability={prediction.probability:.3f} "
            f"recommendation={prediction.recommendation} "
            f"task_type={prediction.task_type} "
            f"elapsed={prediction.elapsed_minutes:.1f}min "
            f"threshold={prediction.sla_threshold:.1f}min"
        )
        self.ops_logger.log(
            op="sla_prediction", file=prediction.task_id, src="sla_predictor",
            outcome="flagged" if prediction.exceeds_threshold else "success",
            detail=detail,
        )
