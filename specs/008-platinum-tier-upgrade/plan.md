# Implementation Plan: Platinum Tier Intelligence Layer

**Branch**: `008-platinum-tier-upgrade` | **Date**: 2026-02-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-platinum-tier-upgrade/spec.md`
**Constitution**: v4.0.0 (Platinum) | **Predecessor**: Gold Tier (007) — 85/85 tasks, 205 tests

## Summary

The Platinum Tier upgrades the Autonomous Employee from a rule-based automation system (Gold) to an intelligent, self-planning, and self-optimizing autonomous system. It introduces an Intelligence Layer above the Gold Execution Engine comprising 7 capabilities: Intelligent Task Planning (P1), Self-Healing Execution (P2), Predictive SLA Monitoring (P3), Dynamic Risk-Based Prioritization (P4), Learning & Optimization Engine (P5), Safe Concurrency Control (P6), and Immutable Audit Logging (P7). All intelligence is heuristic-based (no ML dependencies). Gold Tier functionality remains fully backward-compatible — all 205 existing tests MUST pass without modification.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: frontmatter, watchdog, python-dotenv (existing); no new external dependencies
**Storage**: Obsidian Vault filesystem (Markdown + JSON files); `/Learning_Data/` folder (new)
**Testing**: pytest with PYTHONPATH=src; virtual environment at `.venv/`
**Target Platform**: Local workstation (Linux/WSL2/macOS)
**Project Type**: Single Python project with `src/` layout
**Performance Goals**: No significant degradation vs. Gold; risk score computation < 50ms per task; SLA prediction < 100ms per task
**Constraints**: Heuristic-only intelligence (no ML/LLM); single-process concurrency (threading); all 205 Gold tests must pass unmodified
**Scale/Scope**: 7 new capabilities, 32 functional requirements, 12 new config parameters, 6 new entities, 8 new audit operation types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Functional Foundation | PASS | Platinum extends Gold execution with self-healing cascade and concurrency control |
| II. Vault-Centric Architecture | PASS | `/Learning_Data/` folder added; all other folders preserved |
| III. Perception Layer | PASS | No changes to watchers; Platinum is above the perception layer |
| IV. Reasoning Layer | PASS | Intelligent Planning Engine replaces static plan generation; execution graph stored in `/Plans/` |
| V. Action Layer (Platinum Orchestration) | PASS | Self-healing cascade before rollback; predictive SLA; learning engine |
| VI. Gold Automation Gates | PASS | All 6 gates preserved; Gate 5 extended with Learning Engine data |
| VII. SLA & Success Criteria | PASS | Predictive alerts added; existing SLA thresholds unchanged |
| VIII. Audit & Observability | PASS | 8 new operation types added (additive); append-only log preserved |
| IX. Platinum Intelligence Layer | PASS | All 7 capabilities (P1-P7) addressed in implementation phases |
| Backward Compatibility | PASS | Gold execution flow unchanged; all Platinum features toggleable via ENABLE_* flags |
| No Gold Regression | PASS | 205 existing tests must pass; verified in Phase 11 |

## Project Structure

### Documentation (this feature)

```text
specs/008-platinum-tier-upgrade/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
src/
├── main.py                          # Entry point (modified: wire Platinum modules)
├── intelligence/                    # NEW — Platinum Intelligence Layer
│   ├── __init__.py
│   ├── planning_engine.py           # P1: Intelligent Task Planning
│   ├── execution_graph.py           # P1: ExecutionGraph data model & serialization
│   ├── self_healing.py              # P2: Self-Healing Recovery Cascade
│   ├── sla_predictor.py             # P3: Predictive SLA Monitoring
│   ├── risk_engine.py               # P4: Dynamic Risk-Based Prioritization
│   ├── learning_engine.py           # P5: Learning & Optimization Engine
│   └── concurrency_controller.py    # P6: Safe Concurrency Control
├── processors/
│   ├── task_processor.py            # Modified: integrate Platinum intelligence
│   ├── task_classifier.py           # Unchanged
│   ├── task_executor.py             # Modified: self-healing hooks
│   └── branch_router.py            # Unchanged
├── orchestrator/
│   ├── rollback_manager.py          # Unchanged (Gold fallback preserved)
│   ├── sla_tracker.py               # Modified: predictive SLA integration
│   └── task_mover.py                # Unchanged
├── notifications/
│   ├── notifier.py                  # Modified: Platinum alert types
│   └── webhook_notifier.py          # Unchanged
├── utils/
│   ├── config.py                    # Modified: 12 new Platinum config params
│   ├── dashboard_updater.py         # Modified: Platinum dashboard metrics
│   ├── operations_logger.py         # Modified: 8 new operation types
│   ├── vault_initializer.py         # Modified: create /Learning_Data/ folder
│   ├── vault_manager.py             # Unchanged
│   └── hash_registry.py             # Unchanged
└── security/
    └── (unchanged)

tests/
├── conftest.py                      # Modified: Platinum fixtures
├── unit/
│   ├── test_planning_engine.py      # NEW
│   ├── test_execution_graph.py      # NEW
│   ├── test_self_healing.py         # NEW
│   ├── test_sla_predictor.py        # NEW
│   ├── test_risk_engine.py          # NEW
│   ├── test_learning_engine.py      # NEW
│   ├── test_concurrency_controller.py # NEW
│   └── (all existing Gold tests unchanged)
├── integration/
│   ├── test_platinum_workflow.py     # NEW: Full P1-P7 integration tests
│   └── (all existing Gold tests unchanged)
```

**Structure Decision**: Platinum Intelligence Layer is implemented as a new `src/intelligence/` package, keeping all new modules cleanly separated from Gold Tier code. Gold modules receive minimal, additive modifications (hooks and feature-flag guards) to integrate with the intelligence layer.

---

## Implementation Phases

### Phase 1: Setup & Infrastructure

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T001 | Create `src/intelligence/` package with `__init__.py` | — | simple | Yes | New package for all Platinum modules |
| T002 | Add 12 Platinum config parameters to `config.py` (PREDICTION_THRESHOLD, MAX_PARALLEL_TASKS, LEARNING_WINDOW_DAYS, MAX_RECOVERY_ATTEMPTS, TASK_TIMEOUT_MINUTES, ENABLE_PREDICTIVE_SLA, ENABLE_SELF_HEALING, ENABLE_RISK_SCORING, RISK_WEIGHT_SLA, RISK_WEIGHT_COMPLEXITY, RISK_WEIGHT_IMPACT, RISK_WEIGHT_FAILURE) | — | simple | Yes | All with defaults from spec |
| T003 | Register 8 new Platinum operation types in `operations_logger.py` (sla_prediction, risk_scored, self_heal_retry, self_heal_alternative, self_heal_partial, learning_update, priority_adjusted, concurrency_queued) | — | simple | Yes | Additive to existing VALID_OPS |
| T004 | Update `vault_initializer.py` to create `/Learning_Data/` folder | — | simple | No | Additive; non-breaking |
| T005 | Update `.env.example` with all 12 Platinum parameters | T002 | simple | Yes | Documentation for new config |

### Phase 2: Intelligent Task Planning — P1 (MVP)

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T006 | Create `execution_graph.py`: ExecutionGraph data model with steps[], edges[], priorities[], parallelizable_groups[], to_json(), from_json() | T001 | complex | Yes | Core data structure; serializable to JSON |
| T007 | Create `planning_engine.py`: PlanningEngine class with decompose(task_content) method | T006 | complex | Yes | Main planning interface |
| T008 | Implement keyword-based step decomposition heuristic in PlanningEngine (analyze task content, generate ordered sub-steps based on task type and keywords) | T007 | complex | Yes | Rules-based: keywords map to step templates |
| T009 | Implement dependency identification logic (detect ordering constraints between generated steps, mark independent steps as parallelizable) | T007, T008 | complex | Yes | Graph edge construction |
| T010 | Implement execution graph serialization — save to `/Plans/` alongside markdown plan | T006, T009 | simple | Yes | JSON file write |
| T011 | Integrate PlanningEngine into `task_processor.py` — call decompose() for tasks without manual steps; guard with ENABLE_* flag | T007, T010 | complex | Yes | Replaces Gold fallback plan generator when enabled |
| T012 | Implement Gold fallback: if PlanningEngine fails or is disabled, use existing plan generator unchanged | T011 | simple | Yes | FR-004: backward compatibility |

### Phase 3: Self-Healing Execution — P2 (MVP)

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T013 | Create RecoveryAttempt data model in `self_healing.py` (step_id, strategy, outcome, duration, timestamp) | T001 | simple | Yes | Logging data structure |
| T014 | Create SelfHealingEngine class with recover(failed_step, context) method | T013 | complex | Yes | Main self-healing interface |
| T015 | Implement retry strategy: re-execute failed step (1 attempt) | T014 | simple | Yes | FR-005: first recovery stage |
| T016 | Implement alternative strategy: look up alternative_step in execution graph, execute if defined | T014, T006 | complex | Yes | FR-006: second recovery stage |
| T017 | Implement partial recovery: preserve completed steps, isolate failed step | T014 | complex | Yes | FR-007: third recovery stage |
| T018 | Implement recovery cascade: retry -> alternative -> partial -> Gold fallback (rollback_manager) | T015, T016, T017 | complex | Yes | FR-008: orchestrates all strategies |
| T019 | Add MAX_RECOVERY_ATTEMPTS cap (default: 3) to prevent infinite loops | T018 | simple | Yes | FR-010 |
| T020 | Integrate SelfHealingEngine into `task_processor.py` execution flow — intercept failures before rollback; guard with ENABLE_SELF_HEALING | T018 | complex | Yes | Core integration point |
| T021 | Log every recovery attempt with timestamp, step ID, strategy, outcome, duration | T020, T003 | simple | Yes | FR-009: uses operations_logger |

### Phase 4: Predictive SLA Monitoring — P3 (MVP)

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T022 | Create SLAPrediction data model in `sla_predictor.py` (task_id, predicted_duration, threshold, probability, recommendation, predicted_at) | T001 | simple | Yes | Prediction result structure |
| T023 | Create SLAPredictor class with predict(task, historical_data) method | T022 | complex | Yes | Main prediction interface |
| T024 | Implement statistical prediction: compute breach probability from mean + variance of historical durations (normal distribution approximation) | T023 | complex | Yes | P(duration > threshold) calculation |
| T025 | Implement fallback to Gold SLA estimation (operations log averages) when learning data insufficient | T023 | simple | Yes | FR-013: backward compatibility |
| T026 | Integrate SLAPredictor into processing loop — run prediction for all in-progress tasks each iteration; guard with ENABLE_PREDICTIVE_SLA | T024, T025 | complex | Yes | FR-011: per-iteration prediction |
| T027 | Fire sla_prediction alert when probability > PREDICTION_THRESHOLD; log with task_id, predicted_duration, threshold, probability | T026, T003 | simple | Yes | FR-012, FR-014 |

### Phase 5: Dynamic Risk-Based Prioritization — P4 (MVP)

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T028 | Create RiskScore data model in `risk_engine.py` (sla_risk, complexity, impact, failure_rate, composite_score, computed_at) | T001 | simple | Yes | Score data structure |
| T029 | Create RiskEngine class with compute_score(task, historical_data) method | T028 | complex | Yes | Main risk scoring interface |
| T030 | Implement composite risk score formula: (sla_risk * RISK_WEIGHT_SLA) + (complexity * RISK_WEIGHT_COMPLEXITY) + (impact * RISK_WEIGHT_IMPACT) + (failure_rate * RISK_WEIGHT_FAILURE) | T029 | complex | Yes | FR-015: configurable weights |
| T031 | Implement dynamic execution reordering — sort pending tasks by composite risk score on every loop iteration | T030 | complex | Yes | FR-016: replaces static priority |
| T032 | Integrate RiskEngine into `task_processor.py` — reorder suggest_execution_sequence() output by risk score; guard with ENABLE_RISK_SCORING | T031 | complex | Yes | Core integration with existing priority system |
| T033 | Implement Gold fallback: when risk scoring fails or all scores equal, fall back to Gold static priority ordering | T032 | simple | Yes | FR-018 |
| T034 | Log priority adjustments as priority_adjusted events with old rank, new rank, score components | T032, T003 | simple | Yes | FR-017 |

### Phase 6: Learning & Optimization Engine — P5

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T035 | Create LearningMetrics data model in `learning_engine.py` (task_type, avg_duration, failure_count, total_count, retry_success_rate, sla_compliance_rate, last_updated) | T001 | simple | No | Aggregated metrics structure |
| T036 | Create LearningEngine class with record(task_result), query(task_type), maintenance() methods | T035 | complex | No | Main learning interface |
| T037 | Implement metrics persistence — write execution outcome data to `/Learning_Data/` as JSON after every task completion/failure | T036, T004 | complex | No | FR-019 |
| T038 | Implement running aggregates — compute avg_duration, failure_frequency, retry_success_rate, sla_compliance_rate per task type | T037 | complex | No | FR-020 |
| T039 | Implement data retention — purge records older than LEARNING_WINDOW_DAYS on each maintenance cycle | T036 | simple | No | FR-021 |
| T040 | Wire learning data into PlanningEngine — use historical duration estimates instead of defaults when 5+ data points exist | T036, T007 | complex | No | Connects P5 -> P1 |
| T041 | Wire learning data into RiskEngine — provide historical failure rates for risk score computation | T036, T029 | complex | No | Connects P5 -> P4 |
| T042 | Wire learning data into SLAPredictor — provide duration distribution for breach probability | T036, T023 | complex | No | Connects P5 -> P3 |
| T043 | Log learning_update events after each data persistence | T037, T003 | simple | No | FR-022 |

### Phase 7: Safe Concurrency Control — P6

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T044 | Create ConcurrencySlot data model in `concurrency_controller.py` (task_id, started_at, timeout_at, status) | T001 | simple | No | Slot tracking structure |
| T045 | Create ConcurrencyController class with acquire(), release(), queue(), get_active_count() methods | T044 | complex | No | Main concurrency interface |
| T046 | Implement semaphore-based task limiting — enforce MAX_PARALLEL_TASKS maximum concurrent executions | T045 | complex | No | FR-023 |
| T047 | Implement risk-score-based queue ordering — queue excess tasks in risk-score order (highest first) | T045, T029 | complex | No | FR-024: requires RiskEngine |
| T048 | Implement per-task execution timeout — release resources and mark as failed on timeout (TASK_TIMEOUT_MINUTES) | T045 | complex | No | FR-025 |
| T049 | Integrate ConcurrencyController into processing loop — gate task execution through acquire/release | T046, T048 | complex | No | Core integration |
| T050 | Log concurrency_queued events when tasks are queued due to limit | T049, T003 | simple | No | FR-026 |

### Phase 8: Immutable Platinum Audit Trail — P7

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T051 | Extend operations_logger entry format — add `src` (decision source) field for Platinum entries | T003 | simple | Yes | FR-029: extended log format |
| T052 | Add audit logging calls to PlanningEngine (risk_scored with execution graph details) | T011, T051 | simple | Yes | FR-027 |
| T053 | Add audit logging calls to SelfHealingEngine (self_heal_retry, self_heal_alternative, self_heal_partial) | T020, T051 | simple | Yes | FR-027 |
| T054 | Add audit logging calls to SLAPredictor (sla_prediction with probability and recommendation) | T026, T051 | simple | Yes | FR-027 |
| T055 | Add audit logging calls to RiskEngine (risk_scored, priority_adjusted) | T032, T051 | simple | Yes | FR-027 |
| T056 | Add audit logging calls to LearningEngine (learning_update) | T037, T051 | simple | No | FR-027 |
| T057 | Add audit logging calls to ConcurrencyController (concurrency_queued) | T049, T051 | simple | No | FR-027 |

### Phase 9: Integration & Feature Flags

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T058 | Wire all Platinum modules into main.py processing loop — initialize and connect PlanningEngine, SelfHealingEngine, SLAPredictor, RiskEngine, LearningEngine, ConcurrencyController | T011, T020, T026, T032, T036, T049 | complex | Yes | Master integration point |
| T059 | Add ENABLE_SELF_HEALING feature flag guard — when disabled, skip self-healing cascade and go directly to Gold rollback | T020 | simple | Yes | FR-031 toggle |
| T060 | Add ENABLE_PREDICTIVE_SLA feature flag guard — when disabled, skip SLA prediction loop | T026 | simple | Yes | FR-031 toggle |
| T061 | Add ENABLE_RISK_SCORING feature flag guard — when disabled, use Gold static priority ordering | T032 | simple | Yes | FR-031 toggle |
| T062 | Verify Gold fallback behavior when ALL Platinum features disabled — 205 tests pass, Gold execution unchanged | T058, T059, T060, T061 | complex | Yes | FR-031: full backward compatibility verification |

### Phase 10: Unit Tests

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T063 | Unit tests for ExecutionGraph (serialization, dependency resolution, parallelizable detection) | T006 | complex | Yes | 8-10 tests |
| T064 | Unit tests for PlanningEngine (decomposition, keyword matching, fallback behavior) | T012 | complex | Yes | 8-10 tests |
| T065 | Unit tests for SelfHealingEngine (retry, alternative, partial, cascade, cap) | T019 | complex | Yes | 10-12 tests |
| T066 | Unit tests for SLAPredictor (prediction computation, threshold gating, fallback) | T027 | complex | Yes | 8-10 tests |
| T067 | Unit tests for RiskEngine (score formula, weight configuration, reordering, fallback) | T034 | complex | Yes | 8-10 tests |
| T068 | Unit tests for LearningEngine (persistence, aggregation, retention, query) | T043 | complex | No | 8-10 tests |
| T069 | Unit tests for ConcurrencyController (slot management, queuing, timeout, release) | T050 | complex | No | 8-10 tests |
| T070 | Unit tests for Platinum audit logging (new op types, extended format, src field) | T057 | simple | No | 5-6 tests |

### Phase 11: Integration Tests & Edge Cases

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T071 | Integration test: intelligent planning workflow (high-level task -> execution graph -> ordered execution) | T062 | complex | Yes | US001 acceptance scenarios |
| T072 | Integration test: self-healing recovery cascade (step failure -> retry -> alternative -> partial -> Gold fallback) | T062 | complex | Yes | US002 acceptance scenarios |
| T073 | Integration test: predictive SLA with historical data (populate history -> predict breach -> verify alert) | T062 | complex | Yes | US003 acceptance scenarios |
| T074 | Integration test: risk-based priority reordering (3 tasks with different risk profiles -> risk-ordered execution) | T062 | complex | Yes | US004 acceptance scenarios |
| T075 | Integration test: learning engine data lifecycle (execute tasks -> verify metrics -> verify influence on estimates) | T062 | complex | No | US005 acceptance scenarios |
| T076 | Integration test: concurrency control under load (5 tasks, MAX_PARALLEL=2 -> verify limiting and queuing) | T062 | complex | No | US006 acceptance scenarios |
| T077 | Integration test: full Platinum workflow (all P1-P7 capabilities in one end-to-end flow) | T071, T072, T073, T074, T075, T076 | complex | No | US007 + full regression |
| T078 | Edge case tests: EC-01 (empty task), EC-02 (cascading failures), EC-03 (corrupted learning data), EC-04 (critical task preemption) | T062 | complex | No | Spec edge cases 1-4 |
| T079 | Edge case tests: EC-05 (zero variance), EC-06 (missing risk fields), EC-07 (cold start), EC-08 (file conflict) | T062 | complex | No | Spec edge cases 5-8 |
| T080 | Gold regression verification: run all 205 existing tests, confirm 0 failures | T062 | simple | Yes | FR-030: critical gate |

### Phase 12: Polish & Documentation

| ID | Task | Dependencies | Type | MVP | Notes |
|----|------|-------------|------|-----|-------|
| T081 | Update conftest.py with Platinum test fixtures (learning_data dir, execution_graph factory, recovery_attempt factory) | T063 | complex | Yes | Shared test infrastructure |
| T082 | Update dashboard_updater.py with Platinum metrics (retry success rate, predictive alerts, risk distribution, learning data points) | T058 | complex | No | Constitution VIII dashboard requirements |
| T083 | Update notifier.py with Platinum alert types (predictive SLA warning, self-healing recovery, concurrency limit) | T058 | simple | No | Constitution VIII alerting |
| T084 | Update .env.example with all 12 Platinum parameters and documentation | T005 | simple | Yes | Already partially done |
| T085 | Update README.md for Platinum Tier (architecture overview, new capabilities, configuration) | T080 | complex | No | Hackathon submission |

---

## Critical Path

The critical path (longest sequence of dependent tasks) determines the minimum time to complete the Platinum Tier:

```
T001 (intelligence package)
  -> T006 (ExecutionGraph model)
    -> T007 (PlanningEngine class)
      -> T008 (step decomposition)
        -> T009 (dependency identification)
          -> T010 (graph serialization)
            -> T011 (integrate with task_processor)
              -> T012 (Gold fallback)
                -> T014 (SelfHealingEngine)
                  -> T018 (recovery cascade)
                    -> T020 (integrate self-healing)
                      -> T058 (wire all modules)
                        -> T062 (verify Gold fallback)
                          -> T071-T074 (MVP integration tests)
                            -> T080 (Gold regression)
```

**Critical path length**: 14 sequential tasks (T001 -> T080)

### Parallelizable Groups

The following task groups can execute in parallel once their dependencies are met:

| Group | Tasks | Prerequisite |
|-------|-------|-------------|
| A: Setup | T001, T002, T003, T004 | None (all independent) |
| B: Data Models | T006, T013, T022, T028, T035, T044 | T001 |
| C: SLA + Risk (parallel with Self-Healing) | T023-T027 + T029-T034 | T022/T028 + T001 |
| D: Audit Logging | T051-T057 | T003 + respective engines |
| E: Feature Flags | T059, T060, T061 | Respective engines |
| F: Unit Tests | T063-T070 | Respective modules complete |
| G: Integration Tests | T071-T076 | T062 |

---

## MVP Scope

### MVP Features (must-have for Platinum)

- **P1**: Intelligent Task Planning — auto-decompose tasks into execution graphs
- **P2**: Self-Healing Execution — retry -> alternative -> partial -> Gold fallback
- **P3**: Predictive SLA Monitoring — predict breaches before they occur
- **P4**: Dynamic Risk-Based Prioritization — composite risk score ordering

### Enhancement Features (deliver after MVP)

- **P5**: Learning & Optimization Engine — historical metrics influence future decisions
- **P6**: Safe Concurrency Control — parallel execution with limits
- **P7**: Immutable Platinum Audit Trail (full) — all 8 new operation types logged

### MVP Task Count

| Category | MVP Tasks | Enhancement Tasks | Total |
|----------|-----------|-------------------|-------|
| Phase 1: Setup | 4 | 1 | 5 |
| Phase 2: Planning (P1) | 7 | 0 | 7 |
| Phase 3: Self-Healing (P2) | 9 | 0 | 9 |
| Phase 4: SLA Prediction (P3) | 6 | 0 | 6 |
| Phase 5: Risk Prioritization (P4) | 7 | 0 | 7 |
| Phase 6: Learning Engine (P5) | 0 | 9 | 9 |
| Phase 7: Concurrency (P6) | 0 | 7 | 7 |
| Phase 8: Audit Trail (P7) | 5 | 2 | 7 |
| Phase 9: Integration | 5 | 0 | 5 |
| Phase 10: Unit Tests | 5 | 3 | 8 |
| Phase 11: Integration Tests | 5 | 5 | 10 |
| Phase 12: Polish | 2 | 3 | 5 |
| **Totals** | **55** | **30** | **85** |

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 85 (T001-T085) |
| Total Phases | 12 |
| MVP Tasks | 55 |
| Enhancement Tasks | 30 |
| Simple Tasks | 36 |
| Complex Tasks | 49 |
| Critical Path Length | 14 tasks |
| New Source Files | 8 (in `src/intelligence/`) |
| Modified Source Files | 8 (task_processor, task_executor, sla_tracker, notifier, config, dashboard_updater, operations_logger, vault_initializer) |
| New Test Files | 8 (7 unit + 1 integration) |
| New Config Parameters | 12 |
| New Operation Types | 8 |
| Gold Tests (must pass) | 205 |
| Estimated New Tests | 70-85 |
| User Stories Covered | 7 (US001-US007) |
| Functional Requirements Covered | 32 (FR-001 to FR-032) |
