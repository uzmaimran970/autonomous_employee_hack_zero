"""Unit tests for RiskEngine (Platinum P4)."""

import pytest
from intelligence.risk_engine import RiskEngine, RiskScore, COMPLEXITY_MAP, IMPACT_MAP


class TestRiskScore:
    def test_valid_creation(self):
        s = RiskScore(task_id="t", sla_risk=0.5, complexity=0.33,
                      impact=0.5, failure_rate=0.0, composite_score=0.3)
        assert s.composite_score == 0.3

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            RiskScore(task_id="t", sla_risk=1.5, complexity=0.33,
                      impact=0.5, failure_rate=0.0, composite_score=0.3)

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            RiskScore(task_id="t", sla_risk=-0.1, complexity=0.33,
                      impact=0.5, failure_rate=0.0, composite_score=0.3)


class TestComputeScore:
    def _engine(self, **overrides):
        config = {
            "risk_weight_sla": 0.3, "risk_weight_complexity": 0.2,
            "risk_weight_impact": 0.3, "risk_weight_failure": 0.2,
        }
        config.update(overrides)
        return RiskEngine(config=config)

    def test_all_components_populated(self):
        e = self._engine()
        score = e.compute_score("t", {"classification": "complex", "priority": "critical",
                                       "sla_risk": 0.8}, {"failure_rate": 0.5})
        expected = 0.8 * 0.3 + 0.67 * 0.2 + 1.0 * 0.3 + 0.5 * 0.2
        assert abs(score.composite_score - expected) < 0.01

    def test_default_values_no_history(self):
        e = self._engine()
        score = e.compute_score("t", {})
        assert score.complexity == 0.33  # simple default
        assert score.impact == 0.50  # normal default
        assert score.failure_rate == 0.0

    def test_complexity_map(self):
        assert COMPLEXITY_MAP["simple"] == 0.33
        assert COMPLEXITY_MAP["complex"] == 0.67
        assert COMPLEXITY_MAP["manual_review"] == 1.0

    def test_impact_map(self):
        assert IMPACT_MAP["low"] == 0.25
        assert IMPACT_MAP["normal"] == 0.50
        assert IMPACT_MAP["high"] == 0.75
        assert IMPACT_MAP["critical"] == 1.0

    def test_custom_weights(self):
        e = self._engine(risk_weight_sla=1.0, risk_weight_complexity=0.0,
                         risk_weight_impact=0.0, risk_weight_failure=0.0)
        score = e.compute_score("t", {"sla_risk": 0.5})
        assert abs(score.composite_score - 0.5) < 0.01


class TestReorderTasks:
    def _engine(self):
        return RiskEngine(config={
            "risk_weight_sla": 0.3, "risk_weight_complexity": 0.2,
            "risk_weight_impact": 0.3, "risk_weight_failure": 0.2,
        })

    def test_highest_risk_first(self):
        e = self._engine()
        tasks = [
            ("low.md", {"classification": "simple", "priority": "low", "sla_risk": 0.1}),
            ("high.md", {"classification": "complex", "priority": "critical", "sla_risk": 0.9}),
        ]
        scored = e.reorder_tasks(tasks)
        assert scored[0][0] == "high.md"

    def test_equal_scores_stable(self):
        e = self._engine()
        tasks = [
            ("a.md", {"classification": "simple", "priority": "normal", "sla_risk": 0.5}),
            ("b.md", {"classification": "simple", "priority": "normal", "sla_risk": 0.5}),
        ]
        scored = e.reorder_tasks(tasks)
        assert len(scored) == 2

    def test_handles_scoring_exceptions(self):
        e = self._engine()
        tasks = [("t.md", {"classification": "simple", "priority": "normal", "sla_risk": 0.5})]
        scored = e.reorder_tasks(tasks)
        assert len(scored) == 1

    def test_three_tasks_risk_ordered(self):
        e = self._engine()
        tasks = [
            ("low.md", {"classification": "simple", "priority": "normal", "sla_risk": 0.1}),
            ("high.md", {"classification": "complex", "priority": "critical", "sla_risk": 0.9}),
            ("med.md", {"classification": "simple", "priority": "high", "sla_risk": 0.5}),
        ]
        scored = e.reorder_tasks(tasks)
        assert scored[0][0] == "high.md"
        assert scored[-1][0] == "low.md"
