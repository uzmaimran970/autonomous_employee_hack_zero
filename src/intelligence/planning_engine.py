"""
Intelligent Task Planning Engine for Platinum Tier (P1).

Converts high-level task descriptions into structured execution plans
using keyword-based heuristic decomposition and type-based templates.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from intelligence.execution_graph import ExecutionGraph, ExecutionStep

logger = logging.getLogger(__name__)

# Task type templates: each maps to ordered steps with dependency info
TASK_TEMPLATES = {
    "document": [
        ("read_source", "Read and parse source document", None),
        ("analyze_content", "Analyze document content and structure", None),
        ("generate_output", "Generate processed output", None),
        ("validate_output", "Validate output quality and completeness", None),
        ("save_result", "Save result to vault", None),
    ],
    "email": [
        ("parse_email", "Parse email content and metadata", None),
        ("extract_action", "Extract actionable items from email", None),
        ("draft_response", "Draft response or action plan", None),
        ("review_draft", "Review draft for accuracy", None),
    ],
    "data": [
        ("load_data", "Load raw data files", None),
        ("clean_data", "Clean and normalize data", None),
        ("process_data", "Process and transform data", None),
        ("validate_data", "Validate processed data integrity", None),
        ("export_data", "Export results to target format", None),
    ],
    "code": [
        ("read_requirements", "Read and understand requirements", None),
        ("plan_implementation", "Plan implementation approach", None),
        ("implement_code", "Implement the code changes", None),
        ("test_code", "Test the implementation", None),
        ("review_code", "Review code quality", None),
    ],
    "report": [
        ("gather_data", "Gather data from sources", None),
        ("analyze_data", "Analyze gathered data", None),
        ("generate_report", "Generate report content", None),
        ("format_report", "Format and polish report", None),
        ("review_report", "Review report for accuracy", None),
    ],
    "general": [
        ("understand_task", "Understand task requirements", None),
        ("plan_approach", "Plan execution approach", None),
        ("execute_task", "Execute the main task", None),
        ("verify_result", "Verify task completion", None),
    ],
}

# Keywords that map to task types
TYPE_KEYWORDS = {
    "document": ["document", "file", "pdf", "text", "read", "write", "edit", "format"],
    "email": ["email", "mail", "message", "reply", "forward", "inbox", "send"],
    "data": ["data", "csv", "json", "database", "table", "spreadsheet", "excel", "import", "export"],
    "code": ["code", "program", "script", "function", "bug", "fix", "implement", "develop"],
    "report": ["report", "summary", "quarterly", "analysis", "dashboard", "metric", "chart"],
}


class PlanningEngine:
    """
    Heuristic-based task decomposition engine.

    Converts high-level task descriptions into ExecutionGraphs
    using keyword matching and type-based step templates.
    """

    def __init__(self, vault_path: Path, config: dict, ops_logger=None, learning_engine=None):
        self.vault_path = Path(vault_path)
        self.plans_dir = self.vault_path / "Plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.ops_logger = ops_logger
        self.learning_engine = learning_engine

    def decompose(self, task_content: str, task_type: Optional[str] = None,
                  task_id: str = "unknown") -> ExecutionGraph:
        """
        Decompose a high-level task into a structured execution graph.

        Args:
            task_content: The task description text.
            task_type: Optional explicit task type. Auto-detected if None.
            task_id: Task filename for graph reference.

        Returns:
            ExecutionGraph with ordered steps, dependencies, and priorities.
        """
        if not task_content or not task_content.strip():
            raise ValueError("Task content is empty")

        # Detect task type
        if not task_type:
            task_type = self._extract_task_type(task_content)

        # Get step templates
        template = TASK_TEMPLATES.get(task_type, TASK_TEMPLATES["general"])

        # Build steps with priorities
        steps = []
        for i, (step_id, name, alt_id) in enumerate(template):
            duration = self._get_estimated_duration(task_type, step_id)
            step = ExecutionStep(
                step_id=step_id,
                name=name,
                priority=i + 1,
                estimated_duration=duration,
                alternative_step=alt_id,
            )
            steps.append(step)

        # Build dependency edges (sequential by default)
        edges = {}
        for i in range(len(steps) - 1):
            edges[steps[i].step_id] = [steps[i + 1].step_id]

        # Identify parallelizable groups
        parallelizable = self._find_parallelizable(steps, edges)

        graph = ExecutionGraph(
            task_id=task_id,
            steps=steps,
            edges=edges,
            parallelizable_groups=parallelizable,
        )
        graph.validate()

        # Log
        self._log_decomposition(graph)

        return graph

    def save_graph(self, graph: ExecutionGraph, task_filename: str) -> Path:
        """
        Save execution graph to /Plans/ as JSON.

        Returns:
            Path to the saved graph file.
        """
        graph_path = self.plans_dir / f"{task_filename}.graph.json"
        graph_path.write_text(graph.to_json(), encoding="utf-8")
        return graph_path

    def _extract_task_type(self, content: str) -> str:
        """Extract task type from content using keyword matching."""
        content_lower = content.lower()
        scores = {}

        for task_type, keywords in TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[task_type] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def _get_estimated_duration(self, task_type: str, step_id: str) -> float:
        """Get estimated duration for a step, using learning data if available."""
        default_duration = 1.0  # 1 minute default

        if self.learning_engine:
            metrics = self.learning_engine.query(task_type)
            if metrics and metrics.total_count >= 5:
                # Use historical average divided by typical step count
                template = TASK_TEMPLATES.get(task_type, TASK_TEMPLATES["general"])
                step_count = len(template)
                avg_total = metrics.avg_duration_ms / 60000.0  # ms to minutes
                return avg_total / step_count if step_count > 0 else default_duration

        return default_duration

    def _find_parallelizable(self, steps: list, edges: dict) -> list:
        """Identify groups of steps that can execute in parallel."""
        # Steps with no incoming edges from each other are parallelizable
        dependents = set()
        for dsts in edges.values():
            dependents.update(dsts)

        # Root steps (no dependencies) can be parallel
        roots = [s.step_id for s in steps if s.step_id not in dependents]
        if len(roots) > 1:
            return [roots]
        return []

    def _log_decomposition(self, graph: ExecutionGraph):
        """Log planning engine decomposition."""
        if not self.ops_logger:
            return
        detail = (
            f"steps={len(graph.steps)} edges={sum(len(v) for v in graph.edges.values())} "
            f"parallel_groups={len(graph.parallelizable_groups)}"
        )
        self.ops_logger.log(
            op="risk_scored", file=graph.task_id, src="planning_engine",
            outcome="success", detail=detail,
        )
