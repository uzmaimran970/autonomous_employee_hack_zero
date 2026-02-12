"""Unit tests for SLAPredictor (Platinum P3)."""

import pytest
from intelligence.sla_predictor import SLAPredictor, SLAPrediction


class TestSLAPrediction:
    def test_valid_creation(self):
        p = SLAPrediction(task_id="t", task_type="doc", elapsed_minutes=1.0,
                          predicted_duration=5.0, sla_threshold=10.0,
                          probability=0.3, exceeds_threshold=False,
                          recommendation="on_track")
        assert p.probability == 0.3

    def test_rejects_probability_out_of_range(self):
        with pytest.raises(ValueError, match="probability"):
            SLAPrediction(task_id="t", task_type="doc", elapsed_minutes=1.0,
                          predicted_duration=5.0, sla_threshold=10.0,
                          probability=1.5, exceeds_threshold=False,
                          recommendation="on_track")

    def test_rejects_nonpositive_threshold(self):
        with pytest.raises(ValueError, match="sla_threshold"):
            SLAPrediction(task_id="t", task_type="doc", elapsed_minutes=1.0,
                          predicted_duration=5.0, sla_threshold=0,
                          probability=0.3, exceeds_threshold=False,
                          recommendation="on_track")


class TestPredict:
    def _predictor(self, threshold=0.7):
        return SLAPredictor(config={"prediction_threshold": threshold})

    def test_with_sufficient_history(self):
        p = self._predictor()
        hist = {"avg_duration_ms": 480000, "duration_variance": 3600000000, "total_count": 10}
        pred = p.predict("t", "doc", 5.0, 10.0, historical_data=hist)
        assert 0 <= pred.probability <= 1

    def test_alert_when_exceeds_threshold(self):
        p = self._predictor(threshold=0.1)
        hist = {"avg_duration_ms": 600000, "duration_variance": 90000000000, "total_count": 10}
        pred = p.predict("t", "doc", 9.0, 10.0, historical_data=hist)
        assert pred.exceeds_threshold is True

    def test_no_alert_when_below_threshold(self):
        p = self._predictor(threshold=0.99)
        pred = p.predict("t", "doc", 0.1, 10.0)
        assert pred.exceeds_threshold is False

    def test_zero_variance_no_error(self):
        p = self._predictor()
        hist = {"avg_duration_ms": 120000, "duration_variance": 0, "total_count": 10}
        pred = p.predict("t", "doc", 1.0, 10.0, historical_data=hist)
        assert pred.probability in (0.0, 1.0)

    def test_fallback_with_insufficient_data(self):
        p = self._predictor()
        hist = {"avg_duration_ms": 60000, "duration_variance": 0, "total_count": 2}
        pred = p.predict("t", "doc", 1.0, 10.0, historical_data=hist)
        assert 0 <= pred.probability <= 1

    def test_no_history_fallback(self):
        p = self._predictor()
        pred = p.predict("t", "unknown", 1.0, 10.0)
        assert pred.recommendation in ("on_track", "monitor", "at_risk")

    def test_recommendation_on_track(self):
        p = self._predictor()
        pred = p.predict("t", "doc", 0.1, 100.0)
        assert pred.recommendation == "on_track"

    def test_recommendation_at_risk(self):
        p = self._predictor()
        pred = p.predict("t", "doc", 11.0, 10.0)
        assert pred.recommendation == "at_risk"

    def test_already_breached_returns_one(self):
        p = self._predictor()
        pred = p.predict("t", "doc", 11.0, 10.0)
        assert pred.probability == 1.0
