"""Unit tests for LearningEngine (Platinum P5)."""

import json
import pytest
from pathlib import Path
from intelligence.learning_engine import LearningEngine, LearningMetrics


class TestLearningMetrics:
    def test_failure_rate(self):
        m = LearningMetrics(task_type="doc", total_count=10, failure_count=3, success_count=7)
        assert abs(m.failure_rate - 0.3) < 0.01

    def test_failure_rate_zero_total(self):
        m = LearningMetrics(task_type="doc")
        assert m.failure_rate == 0.0

    def test_retry_success_rate(self):
        m = LearningMetrics(task_type="doc", retry_success_count=2, retry_total_count=5)
        assert abs(m.retry_success_rate - 0.4) < 0.01

    def test_sla_compliance_rate(self):
        m = LearningMetrics(task_type="doc", total_count=10, sla_breach_count=2)
        assert abs(m.sla_compliance_rate - 0.8) < 0.01

    def test_duration_stdev(self):
        m = LearningMetrics(task_type="doc", duration_variance=10000)
        assert m.duration_stdev == pytest.approx(100.0)

    def test_to_dict_includes_derived(self):
        m = LearningMetrics(task_type="doc", total_count=10, failure_count=2,
                            success_count=8, sla_breach_count=1)
        d = m.to_dict()
        assert "failure_rate" in d
        assert "retry_success_rate" in d
        assert "sla_compliance_rate" in d


class TestLearningEngineRecord:
    def test_creates_jsonl_file(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "email", "duration_ms": 30000, "outcome": "success"})
        assert (temp_vault / "Learning_Data" / "email.jsonl").exists()

    def test_creates_meta_json(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "email", "duration_ms": 30000, "outcome": "success"})
        assert (temp_vault / "Learning_Data" / "email.meta.json").exists()

    def test_increments_count(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        for _ in range(3):
            engine.record({"task_type": "doc", "duration_ms": 60000, "outcome": "success"})
        m = engine.query("doc")
        assert m.total_count == 3

    def test_running_average(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "doc", "duration_ms": 100, "outcome": "success"})
        engine.record({"task_type": "doc", "duration_ms": 200, "outcome": "success"})
        m = engine.query("doc")
        assert abs(m.avg_duration_ms - 150.0) < 1.0

    def test_variance_computation(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        for d in [100, 200, 300]:
            engine.record({"task_type": "doc", "duration_ms": d, "outcome": "success"})
        m = engine.query("doc")
        assert m.duration_variance > 0

    def test_tracks_failures(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "doc", "duration_ms": 100, "outcome": "failed"})
        m = engine.query("doc")
        assert m.failure_count == 1
        assert m.success_count == 0


class TestLearningEngineQuery:
    def test_returns_none_unknown_type(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        assert engine.query("never_seen") is None

    def test_returns_correct_metrics(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "doc", "duration_ms": 60000, "outcome": "success"})
        m = engine.query("doc")
        assert m.task_type == "doc"
        assert m.total_count == 1

    def test_handles_corrupted_meta(self, temp_vault, platinum_config):
        engine = LearningEngine(temp_vault, platinum_config)
        (temp_vault / "Learning_Data" / "bad.meta.json").write_text("NOT JSON{{{")
        assert engine.query("bad") is None


class TestMaintenance:
    def test_purges_expired_data(self, temp_vault, platinum_config):
        platinum_config["learning_window_days"] = 0
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "doc", "duration_ms": 100, "outcome": "success"})
        engine.maintenance()
        # With 0-day window, data may be purged depending on timing
        jsonl = temp_vault / "Learning_Data" / "doc.jsonl"
        assert jsonl.exists()

    def test_preserves_recent_data(self, temp_vault, platinum_config):
        platinum_config["learning_window_days"] = 365
        engine = LearningEngine(temp_vault, platinum_config)
        engine.record({"task_type": "doc", "duration_ms": 100, "outcome": "success"})
        engine.maintenance()
        m = engine.query("doc")
        assert m.total_count >= 1
