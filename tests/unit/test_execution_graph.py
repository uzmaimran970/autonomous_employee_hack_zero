"""Unit tests for ExecutionGraph and ExecutionStep (Platinum P1)."""

import json
import pytest
from intelligence.execution_graph import ExecutionGraph, ExecutionStep


class TestExecutionStep:
    def test_valid_creation(self):
        step = ExecutionStep(step_id="s1", name="Read", priority=1)
        assert step.step_id == "s1"
        assert step.status == "pending"

    def test_rejects_invalid_priority(self):
        with pytest.raises(ValueError, match="priority"):
            ExecutionStep(step_id="s1", name="Bad", priority=0)

    def test_rejects_negative_priority(self):
        with pytest.raises(ValueError, match="priority"):
            ExecutionStep(step_id="s1", name="Bad", priority=-1)

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            ExecutionStep(step_id="s1", name="Bad", priority=1, status="unknown")

    def test_all_valid_statuses(self):
        for status in ("pending", "in_progress", "completed", "failed"):
            step = ExecutionStep(step_id="s1", name="Step", priority=1, status=status)
            assert step.status == status

    def test_optional_fields_default_none(self):
        step = ExecutionStep(step_id="s1", name="Step", priority=1)
        assert step.estimated_duration is None
        assert step.alternative_step is None


class TestExecutionGraph:
    def _make_graph(self, step_count=3):
        steps = [ExecutionStep(step_id=f"s{i}", name=f"Step {i}", priority=i + 1)
                 for i in range(step_count)]
        edges = {f"s{i}": [f"s{i+1}"] for i in range(step_count - 1)}
        return ExecutionGraph(task_id="test.md", steps=steps, edges=edges)

    def test_to_json_from_json_roundtrip(self):
        graph = self._make_graph()
        json_str = graph.to_json()
        restored = ExecutionGraph.from_json(json_str)
        assert restored.task_id == "test.md"
        assert len(restored.steps) == 3
        assert len(restored.edges) == 2

    def test_validate_rejects_empty_steps(self):
        graph = ExecutionGraph(task_id="test.md", steps=[], edges={})
        with pytest.raises(ValueError, match="at least 1 step"):
            graph.validate()

    def test_validate_rejects_circular_deps(self):
        steps = [ExecutionStep(step_id=f"s{i}", name=f"Step {i}", priority=i + 1) for i in range(3)]
        edges = {"s0": ["s1"], "s1": ["s2"], "s2": ["s0"]}
        graph = ExecutionGraph(task_id="test.md", steps=steps, edges=edges)
        with pytest.raises(ValueError, match="circular"):
            graph.validate()

    def test_validate_rejects_unknown_edge_source(self):
        steps = [ExecutionStep(step_id="s0", name="Step 0", priority=1)]
        edges = {"unknown": ["s0"]}
        graph = ExecutionGraph(task_id="test.md", steps=steps, edges=edges)
        with pytest.raises(ValueError, match="not found"):
            graph.validate()

    def test_validate_rejects_unknown_edge_dest(self):
        steps = [ExecutionStep(step_id="s0", name="Step 0", priority=1)]
        edges = {"s0": ["unknown"]}
        graph = ExecutionGraph(task_id="test.md", steps=steps, edges=edges)
        with pytest.raises(ValueError, match="not found"):
            graph.validate()

    def test_validate_passes_valid_graph(self):
        graph = self._make_graph()
        assert graph.validate() is True

    def test_get_execution_order_topological(self):
        graph = self._make_graph()
        order = graph.get_execution_order()
        ids = [s.step_id for s in order]
        assert ids == ["s0", "s1", "s2"]

    def test_version_defaults_to_one(self):
        graph = self._make_graph()
        assert graph.version == 1

    def test_created_at_auto_set(self):
        graph = self._make_graph()
        assert graph.created_at != ""
