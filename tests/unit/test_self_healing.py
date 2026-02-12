"""Unit tests for SelfHealingEngine (Platinum P2)."""

import pytest
from intelligence.self_healing import SelfHealingEngine, RecoveryAttempt
from intelligence.execution_graph import ExecutionStep


class TestRecoveryAttempt:
    def test_valid_creation(self):
        a = RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                            strategy="retry", outcome="success", duration_ms=10.0)
        assert a.strategy == "retry"

    def test_rejects_invalid_strategy(self):
        with pytest.raises(ValueError, match="strategy"):
            RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                            strategy="invalid", outcome="success", duration_ms=1.0)

    def test_rejects_invalid_outcome(self):
        with pytest.raises(ValueError, match="outcome"):
            RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                            strategy="retry", outcome="unknown", duration_ms=1.0)

    def test_rejects_negative_duration(self):
        with pytest.raises(ValueError, match="duration_ms"):
            RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                            strategy="retry", outcome="failed", duration_ms=-1.0)

    def test_all_strategies_accepted(self):
        for s in ("retry", "alternative", "partial"):
            a = RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                                strategy=s, outcome="success", duration_ms=1.0)
            assert a.strategy == s

    def test_to_dict(self):
        a = RecoveryAttempt(task_id="t", step_id="s", attempt_number=1,
                            strategy="retry", outcome="failed", duration_ms=5.0)
        d = a.to_dict()
        assert d["strategy"] == "retry"
        assert "timestamp" in d


class TestRetryStrategy:
    def test_succeeds_when_fn_returns_true(self, platinum_config):
        engine = SelfHealingEngine(config=platinum_config)
        step = ExecutionStep(step_id="s1", name="Test", priority=1)
        attempts = engine.recover("task.md", step, execute_fn=lambda s: True)
        assert attempts[0].strategy == "retry"
        assert attempts[0].outcome == "success"

    def test_fails_when_fn_returns_false(self, platinum_config):
        engine = SelfHealingEngine(config=platinum_config)
        step = ExecutionStep(step_id="s1", name="Test", priority=1)
        attempts = engine.recover("task.md", step, execute_fn=lambda s: False)
        assert attempts[0].strategy == "retry"
        assert attempts[0].outcome == "failed"

    def test_fails_when_fn_raises(self, platinum_config):
        engine = SelfHealingEngine(config=platinum_config)
        step = ExecutionStep(step_id="s1", name="Test", priority=1)
        attempts = engine.recover("task.md", step,
                                  execute_fn=lambda s: (_ for _ in ()).throw(RuntimeError("Boom")))
        assert attempts[0].outcome == "failed"
        assert "Boom" in attempts[0].error_detail


class TestAlternativeStrategy:
    def test_succeeds_with_alt_step(self, platinum_config, make_execution_graph):
        engine = SelfHealingEngine(config=platinum_config)
        graph = make_execution_graph(step_count=3, with_alternatives=True)
        failed = graph.steps[1]
        call_count = {"n": 0}
        def fn(s):
            call_count["n"] += 1
            return call_count["n"] > 1  # retry fails, alt succeeds
        attempts = engine.recover("task.md", failed, execution_graph=graph, execute_fn=fn)
        strategies = [a.strategy for a in attempts]
        assert "alternative" in strategies

    def test_skipped_when_no_alt(self, platinum_config, make_execution_graph):
        engine = SelfHealingEngine(config=platinum_config)
        graph = make_execution_graph(step_count=3, with_alternatives=False)
        failed = graph.steps[0]
        attempts = engine.recover("task.md", failed, execution_graph=graph,
                                  execute_fn=lambda s: False)
        assert "alternative" not in [a.strategy for a in attempts]


class TestPartialRecovery:
    def test_succeeds_with_completed_steps(self, platinum_config, make_execution_graph):
        engine = SelfHealingEngine(config=platinum_config)
        graph = make_execution_graph(step_count=3)
        graph.steps[0].status = "completed"
        attempts = engine.recover("task.md", graph.steps[2],
                                  execution_graph=graph, execute_fn=lambda s: False)
        partials = [a for a in attempts if a.strategy == "partial"]
        assert partials[0].outcome == "success"

    def test_fails_with_no_completed(self, platinum_config, make_execution_graph):
        engine = SelfHealingEngine(config=platinum_config)
        graph = make_execution_graph(step_count=3)
        attempts = engine.recover("task.md", graph.steps[1],
                                  execution_graph=graph, execute_fn=lambda s: False)
        partials = [a for a in attempts if a.strategy == "partial"]
        assert partials[0].outcome == "failed"


class TestCascade:
    def test_full_cascade_all_fail(self, platinum_config, make_execution_graph):
        engine = SelfHealingEngine(config=platinum_config)
        graph = make_execution_graph(step_count=3, with_alternatives=True)
        attempts = engine.recover("task.md", graph.steps[1],
                                  execution_graph=graph, execute_fn=lambda s: False)
        assert len(attempts) == 3
        assert [a.strategy for a in attempts] == ["retry", "alternative", "partial"]
        assert all(a.outcome == "failed" for a in attempts)

    def test_max_attempts_cap(self):
        engine = SelfHealingEngine(config={"max_recovery_attempts": 1})
        step = ExecutionStep(step_id="s1", name="Test", priority=1)
        attempts = engine.recover("task.md", step, execute_fn=lambda s: False)
        assert len(attempts) == 1
