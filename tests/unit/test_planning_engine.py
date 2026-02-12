"""Unit tests for PlanningEngine (Platinum P1)."""

import json
import pytest
from intelligence.planning_engine import PlanningEngine, TASK_TEMPLATES, TYPE_KEYWORDS
from intelligence.execution_graph import ExecutionGraph


class TestDecompose:
    def _engine(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Plans").mkdir()
        return PlanningEngine(vault_path=vault, config={})

    def test_document_produces_3_plus_steps(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Read the quarterly document", task_type="document")
        assert len(graph.steps) >= 3

    def test_email_produces_3_plus_steps(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Reply to client email", task_type="email")
        assert len(graph.steps) >= 3

    def test_data_step_count_matches_template(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Process CSV data", task_type="data")
        assert len(graph.steps) == len(TASK_TEMPLATES["data"])

    def test_report_step_count_matches_template(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Generate report", task_type="report")
        assert len(graph.steps) == len(TASK_TEMPLATES["report"])

    def test_raises_on_empty_content(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            self._engine(tmp_path).decompose("")

    def test_raises_on_whitespace_content(self, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            self._engine(tmp_path).decompose("   \n\t  ")

    def test_generates_sequential_edges(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Process data", task_type="data")
        ids = [s.step_id for s in graph.steps]
        for i in range(len(ids) - 1):
            assert ids[i] in graph.edges
            assert ids[i + 1] in graph.edges[ids[i]]

    def test_graph_validates(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Fix code bug", task_type="code")
        assert graph.validate() is True

    def test_assigns_incrementing_priorities(self, tmp_path):
        graph = self._engine(tmp_path).decompose("General task", task_type="general")
        priorities = [s.priority for s in graph.steps]
        assert priorities == list(range(1, len(graph.steps) + 1))

    def test_auto_detects_email_type(self, tmp_path):
        graph = self._engine(tmp_path).decompose("Send reply to inbox email message")
        email_ids = [t[0] for t in TASK_TEMPLATES["email"]]
        assert [s.step_id for s in graph.steps] == email_ids


class TestExtractTaskType:
    def _engine(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        return PlanningEngine(vault_path=vault, config={})

    def test_quarterly_report_maps_to_report(self, tmp_path):
        assert self._engine(tmp_path)._extract_task_type("Generate quarterly report") == "report"

    def test_parse_email_maps_to_email(self, tmp_path):
        assert self._engine(tmp_path)._extract_task_type("Parse incoming email") == "email"

    def test_unknown_defaults_to_general(self, tmp_path):
        assert self._engine(tmp_path)._extract_task_type("Do something unusual") == "general"

    def test_data_keywords_detected(self, tmp_path):
        assert self._engine(tmp_path)._extract_task_type("Import CSV data from database table") == "data"


class TestSaveGraph:
    def test_writes_json_to_plans_dir(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        engine = PlanningEngine(vault_path=vault, config={})
        graph = engine.decompose("Document task", task_type="document", task_id="doc.md")
        path = engine.save_graph(graph, "doc.md")
        assert path.exists()
        assert path.parent.name == "Plans"
        data = json.loads(path.read_text())
        assert data["task_id"] == "doc.md"
        assert len(data["steps"]) >= 3
