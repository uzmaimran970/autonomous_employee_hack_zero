"""
Execution Graph data model for Platinum Intelligent Task Planning (P1).

Represents a task's execution plan as a directed acyclic graph (DAG)
with ordered steps, dependency edges, and parallelizable groups.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class ExecutionStep:
    """A single step in an execution graph."""

    step_id: str
    name: str
    priority: int
    status: str = "pending"
    estimated_duration: Optional[float] = None
    alternative_step: Optional[str] = None

    def __post_init__(self):
        if self.priority < 1:
            raise ValueError(f"priority must be >= 1, got {self.priority}")
        valid_statuses = {"pending", "in_progress", "completed", "failed"}
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")


@dataclass
class ExecutionGraph:
    """
    Structured representation of a task's execution plan with dependencies.

    Uses an adjacency list (edges) where each key is a step_id and the value
    is a list of step_ids that depend on it (must run after it).
    """

    task_id: str
    steps: list = field(default_factory=list)
    edges: dict = field(default_factory=dict)
    parallelizable_groups: list = field(default_factory=list)
    created_at: str = ""
    version: int = 1

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def validate(self) -> bool:
        """
        Validate the execution graph.

        Checks:
        - At least 1 step exists
        - All step_ids in edges exist in steps
        - No circular dependencies (DAG property)

        Returns:
            True if valid.

        Raises:
            ValueError: If validation fails.
        """
        if not self.steps:
            raise ValueError("ExecutionGraph must have at least 1 step")

        step_ids = {s.step_id for s in self.steps}

        # Validate edges reference existing steps
        for src, dsts in self.edges.items():
            if src not in step_ids:
                raise ValueError(f"Edge source '{src}' not found in steps")
            for dst in dsts:
                if dst not in step_ids:
                    raise ValueError(f"Edge destination '{dst}' not found in steps")

        # Validate DAG (no circular dependencies) via topological sort
        in_degree = {s.step_id: 0 for s in self.steps}
        for src, dsts in self.edges.items():
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for dst in self.edges.get(node, []):
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)

        if visited != len(self.steps):
            raise ValueError("ExecutionGraph contains circular dependencies")

        return True

    def get_execution_order(self) -> list:
        """
        Return steps in topological order (respecting dependencies).

        Returns:
            List of ExecutionStep in execution order.
        """
        step_map = {s.step_id: s for s in self.steps}
        in_degree = {s.step_id: 0 for s in self.steps}
        for src, dsts in self.edges.items():
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = sorted(
            [sid for sid, deg in in_degree.items() if deg == 0],
            key=lambda sid: step_map[sid].priority
        )
        result = []
        while queue:
            node = queue.pop(0)
            result.append(step_map[node])
            for dst in self.edges.get(node, []):
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)
            queue.sort(key=lambda sid: step_map[sid].priority)

        return result

    def to_json(self) -> str:
        """Serialize the execution graph to JSON string."""
        data = {
            "task_id": self.task_id,
            "steps": [asdict(s) for s in self.steps],
            "edges": self.edges,
            "parallelizable_groups": self.parallelizable_groups,
            "created_at": self.created_at,
            "version": self.version,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ExecutionGraph":
        """Reconstruct an ExecutionGraph from a JSON string."""
        data = json.loads(json_str)
        steps = [ExecutionStep(**s) for s in data["steps"]]
        return cls(
            task_id=data["task_id"],
            steps=steps,
            edges=data.get("edges", {}),
            parallelizable_groups=data.get("parallelizable_groups", []),
            created_at=data.get("created_at", ""),
            version=data.get("version", 1),
        )
