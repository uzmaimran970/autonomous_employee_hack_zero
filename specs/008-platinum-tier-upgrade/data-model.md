# Data Model: Platinum Tier Intelligence Layer

**Feature**: 008-platinum-tier-upgrade | **Date**: 2026-02-11 | **Phase**: 1

## Purpose

Define all data entities introduced by the Platinum Intelligence Layer, their attributes, relationships, validation rules, and state transitions.

---

## Entities

### 1. ExecutionGraph

**Location**: `src/intelligence/execution_graph.py`
**Purpose**: Structured representation of a task's execution plan with ordered steps and dependencies.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | Reference to the source task filename |
| steps | list[ExecutionStep] | Yes | Ordered list of execution steps |
| edges | dict[str, list[str]] | Yes | Adjacency list: step_id -> [dependent_step_ids] |
| parallelizable_groups | list[list[str]] | No | Groups of step IDs that can execute concurrently |
| created_at | str (ISO) | Yes | Timestamp of graph creation |
| version | int | Yes | Graph version (incremented on re-planning) |

#### ExecutionStep (embedded)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| step_id | str | Yes | Unique identifier (e.g., "step_1") |
| name | str | Yes | Human-readable step description |
| priority | int | Yes | Step-level priority (1=highest) |
| estimated_duration | float | No | Estimated duration in minutes (from learning data or default) |
| alternative_step | str | No | ID of alternative step for self-healing |
| status | str | Yes | pending / in_progress / completed / failed |

**Validation rules**:
- steps list must have at least 1 step
- All step_ids in edges must exist in steps
- No circular dependencies (DAG validation)
- priority values must be positive integers

**State transitions**:
```
pending -> in_progress -> completed
pending -> in_progress -> failed
```

**Serialization**: `to_json()` -> JSON file in `/Plans/`; `from_json()` -> reconstruct from file

---

### 2. RiskScore

**Location**: `src/intelligence/risk_engine.py`
**Purpose**: Composite score for dynamic task prioritization.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | Reference to task filename |
| sla_risk | float | Yes | SLA breach probability (0.0-1.0) |
| complexity | float | Yes | Normalized complexity (0.33/0.67/1.0) |
| impact | float | Yes | Normalized business impact (0.25/0.5/0.75/1.0) |
| failure_rate | float | Yes | Historical failure rate (0.0-1.0) |
| composite_score | float | Yes | Weighted sum of components |
| computed_at | str (ISO) | Yes | Timestamp of computation |

**Validation rules**:
- All float components must be in range [0.0, 1.0]
- composite_score = (sla_risk * w1) + (complexity * w2) + (impact * w3) + (failure_rate * w4) where w1+w2+w3+w4=1.0
- computed_at must be valid ISO timestamp

**Complexity mapping**:
- simple -> 0.33
- complex -> 0.67
- manual_review -> 1.0

**Impact mapping** (from task priority field):
- low -> 0.25
- normal -> 0.50
- high -> 0.75
- critical -> 1.0

---

### 3. RecoveryAttempt

**Location**: `src/intelligence/self_healing.py`
**Purpose**: Record of a single self-healing attempt on a failed step.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | Reference to task filename |
| step_id | str | Yes | ID of the failed step |
| attempt_number | int | Yes | Attempt number (1-3, capped by MAX_RECOVERY_ATTEMPTS) |
| strategy | str | Yes | Strategy name: "retry", "alternative", "partial" |
| outcome | str | Yes | "success" or "failed" |
| duration_ms | float | Yes | Duration of recovery attempt in milliseconds |
| timestamp | str (ISO) | Yes | When the attempt occurred |
| error_detail | str | No | Error message if outcome is "failed" |

**Validation rules**:
- strategy must be one of: "retry", "alternative", "partial"
- outcome must be one of: "success", "failed"
- attempt_number must be between 1 and MAX_RECOVERY_ATTEMPTS (default 3)
- duration_ms must be non-negative

**State machine** (per task):
```
step_failed -> retry (attempt 1)
  -> success: continue execution
  -> failed: alternative (attempt 2)
    -> success: continue execution
    -> failed: partial (attempt 3)
      -> success: mark failed step, continue with remaining
      -> failed: Gold rollback
```

---

### 4. LearningMetrics

**Location**: `src/intelligence/learning_engine.py`
**Purpose**: Aggregated historical execution data per task type.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_type | str | Yes | Task type identifier (e.g., "document", "email") |
| total_count | int | Yes | Total tasks of this type processed |
| success_count | int | Yes | Tasks completed successfully |
| failure_count | int | Yes | Tasks that failed |
| avg_duration_ms | float | Yes | Running average execution duration |
| duration_variance | float | Yes | Variance of execution durations (for SLA prediction) |
| retry_success_count | int | Yes | Successful self-healing recoveries |
| retry_total_count | int | Yes | Total self-healing attempts |
| sla_breach_count | int | Yes | Tasks that breached SLA |
| last_updated | str (ISO) | Yes | Last time metrics were updated |

**Derived metrics** (computed, not stored):
- `failure_rate` = failure_count / total_count
- `retry_success_rate` = retry_success_count / retry_total_count (0 if no retries)
- `sla_compliance_rate` = 1 - (sla_breach_count / total_count)
- `duration_stdev` = sqrt(duration_variance)

**Validation rules**:
- total_count = success_count + failure_count
- All counts must be non-negative
- avg_duration_ms must be non-negative
- duration_variance must be non-negative

**Storage**: One JSON file per task_type in `/Learning_Data/`, e.g., `/Learning_Data/document.json`

**Retention**: Records older than LEARNING_WINDOW_DAYS are purged on maintenance cycle

---

### 5. SLAPrediction

**Location**: `src/intelligence/sla_predictor.py`
**Purpose**: Predicted SLA breach probability for an in-progress task.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | Reference to task filename |
| task_type | str | Yes | Task type for historical lookup |
| elapsed_minutes | float | Yes | Time elapsed since task started |
| predicted_duration | float | Yes | Predicted total duration in minutes |
| sla_threshold | float | Yes | SLA threshold in minutes |
| probability | float | Yes | Breach probability (0.0-1.0) |
| exceeds_threshold | bool | Yes | True if probability > PREDICTION_THRESHOLD |
| recommendation | str | Yes | Human-readable action recommendation |
| predicted_at | str (ISO) | Yes | Timestamp of prediction |

**Validation rules**:
- probability must be in range [0.0, 1.0]
- elapsed_minutes and predicted_duration must be non-negative
- sla_threshold must be positive
- exceeds_threshold must match (probability > PREDICTION_THRESHOLD)

**Recommendation values**:
- "on_track" — probability < 0.3
- "monitor" — probability 0.3-0.7
- "at_risk" — probability > 0.7 (alert fires)

---

### 6. ConcurrencySlot

**Location**: `src/intelligence/concurrency_controller.py`
**Purpose**: Tracks an active concurrent execution slot.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slot_id | int | Yes | Slot number (0 to MAX_PARALLEL_TASKS-1) |
| task_id | str | Yes | Reference to task filename occupying the slot |
| started_at | str (ISO) | Yes | When task execution started |
| timeout_at | str (ISO) | Yes | When task should be forcefully terminated |
| status | str | Yes | "active", "completed", "timed_out", "released" |

**Validation rules**:
- slot_id must be in range [0, MAX_PARALLEL_TASKS)
- timeout_at must be after started_at
- status must be one of: "active", "completed", "timed_out", "released"

**State transitions**:
```
(empty) -> active (acquire)
active -> completed (normal finish)
active -> timed_out (timeout exceeded)
active -> released (manual release)
completed -> (empty) (release)
timed_out -> (empty) (release)
released -> (empty) (release)
```

---

## Entity Relationships

```
Task File (Vault)
  |
  ├── ExecutionGraph (1:1) — generated by PlanningEngine
  |     └── ExecutionStep (1:N) — steps within the graph
  |
  ├── RiskScore (1:1) — computed by RiskEngine each iteration
  |
  ├── RecoveryAttempt (1:N) — created by SelfHealingEngine on failure
  |
  ├── SLAPrediction (1:N) — computed by SLAPredictor each iteration
  |
  └── ConcurrencySlot (1:1) — assigned by ConcurrencyController during execution

LearningMetrics (per task_type, shared across tasks)
  ├── Feeds into PlanningEngine (duration estimates)
  ├── Feeds into RiskEngine (failure rates)
  └── Feeds into SLAPredictor (duration distribution)
```

---

## Existing Entities (unchanged)

These Gold Tier entities remain unmodified:

| Entity | Location | Platinum Impact |
|--------|----------|-----------------|
| Task file (frontmatter) | Vault markdown files | No changes; Platinum reads existing fields |
| Operations log entry | `operations.log` (JSON Lines) | 8 new op types added (additive) |
| Rollback snapshot | `/Rollback_Archive/` | Unchanged; used as Gold fallback |
| Dashboard metrics | `Dashboard.md` | Extended with Platinum metrics (additive) |
| Config parameters | `.env` + `config.py` | 12 new parameters added (additive) |
