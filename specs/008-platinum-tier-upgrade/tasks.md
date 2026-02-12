# Tasks: Platinum Tier Intelligence Layer

**Input**: Design documents from `/specs/008-platinum-tier-upgrade/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md
**Branch**: `008-platinum-tier-upgrade`
**Gold Baseline**: 205 tests passing | 85/85 Gold tasks complete

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the intelligence package structure, register Platinum config and operation types. All existing Gold code remains untouched.

- [x] T001 [P] Create `src/intelligence/__init__.py` with package docstring for Platinum Intelligence Layer
- [x] T002 [P] Add 12 Platinum config parameters to `src/utils/config.py` — PREDICTION_THRESHOLD (0.7), MAX_PARALLEL_TASKS (3), LEARNING_WINDOW_DAYS (30), MAX_RECOVERY_ATTEMPTS (3), TASK_TIMEOUT_MINUTES (15), ENABLE_PREDICTIVE_SLA (true), ENABLE_SELF_HEALING (true), ENABLE_RISK_SCORING (true), RISK_WEIGHT_SLA (0.3), RISK_WEIGHT_COMPLEXITY (0.2), RISK_WEIGHT_IMPACT (0.3), RISK_WEIGHT_FAILURE (0.2)
- [x] T003 [P] Register 8 new Platinum operation types in `src/utils/operations_logger.py` — add sla_prediction, risk_scored, self_heal_retry, self_heal_alternative, self_heal_partial, learning_update, priority_adjusted, concurrency_queued to VALID_OPS
- [x] T004 [P] Update `src/utils/vault_initializer.py` to create `/Learning_Data/` folder during vault initialization
- [x] T005 Update `.env.example` with all 12 Platinum parameters including descriptions and default values

**Checkpoint**: Intelligence package exists, config loaded, operation types registered. Gold tests still pass (205/205).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared data models and base classes used across multiple user stories. MUST complete before user story implementation begins.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 [P] Create ExecutionStep dataclass in `src/intelligence/execution_graph.py` — fields: step_id (str), name (str), priority (int), estimated_duration (float|None), alternative_step (str|None), status (str, default "pending"); validate priority > 0, status in {pending, in_progress, completed, failed}
- [x] T007 [P] Create ExecutionGraph dataclass in `src/intelligence/execution_graph.py` — fields: task_id (str), steps (list[ExecutionStep]), edges (dict[str, list[str]]), parallelizable_groups (list[list[str]]), created_at (str), version (int); implement to_json() and from_json() for serialization; validate DAG (no circular deps), all edge step_ids exist in steps
- [x] T008 [P] Create RecoveryAttempt dataclass in `src/intelligence/self_healing.py` — fields: task_id (str), step_id (str), attempt_number (int), strategy (str), outcome (str), duration_ms (float), timestamp (str), error_detail (str|None); validate strategy in {retry, alternative, partial}, outcome in {success, failed}, attempt_number between 1 and MAX_RECOVERY_ATTEMPTS
- [x] T009 [P] Create RiskScore dataclass in `src/intelligence/risk_engine.py` — fields: task_id (str), sla_risk (float), complexity (float), impact (float), failure_rate (float), composite_score (float), computed_at (str); validate all floats in [0.0, 1.0]; add COMPLEXITY_MAP (simple=0.33, complex=0.67, manual_review=1.0) and IMPACT_MAP (low=0.25, normal=0.50, high=0.75, critical=1.0)
- [x] T010 [P] Create SLAPrediction dataclass in `src/intelligence/sla_predictor.py` — fields: task_id (str), task_type (str), elapsed_minutes (float), predicted_duration (float), sla_threshold (float), probability (float), exceeds_threshold (bool), recommendation (str), predicted_at (str); validate probability in [0.0, 1.0], sla_threshold > 0
- [x] T011 [P] Create LearningMetrics dataclass in `src/intelligence/learning_engine.py` — fields: task_type (str), total_count (int), success_count (int), failure_count (int), avg_duration_ms (float), duration_variance (float), retry_success_count (int), retry_total_count (int), sla_breach_count (int), last_updated (str); add derived property methods: failure_rate, retry_success_rate, sla_compliance_rate, duration_stdev
- [x] T012 [P] Create ConcurrencySlot dataclass in `src/intelligence/concurrency_controller.py` — fields: slot_id (int), task_id (str), started_at (str), timeout_at (str), status (str); validate status in {active, completed, timed_out, released}
- [x] T013 Extend operations_logger entry format in `src/utils/operations_logger.py` — add optional `src` (decision source) field for Platinum log entries; maintain backward compatibility for Gold entries that don't include `src`
- [x] T014 Update `tests/conftest.py` with Platinum test fixtures — add `learning_data_dir` fixture (creates tmp Learning_Data folder), `make_execution_graph` factory fixture, `make_recovery_attempt` factory fixture, `make_risk_score` factory fixture

**Checkpoint**: All 6 Platinum entities defined with validation. Shared fixtures ready. Gold tests still pass (205/205).

---

## Phase 3: User Story 1 — Intelligent Task Planning (Priority: P1) MVP

**Goal**: System auto-decomposes high-level task requests into structured execution plans with ordered sub-steps, dependencies, and per-step priority.

**Independent Test**: Create a task file with "Organize quarterly report from raw data files". Verify system generates a plan with 3+ ordered steps, dependency edges, and priority assignments stored as JSON execution graph in `/Plans/`.

### Implementation for User Story 1

- [x] T015 [US1] Create PlanningEngine class in `src/intelligence/planning_engine.py` — constructor accepts vault_path and config; implement decompose(task_content: str, task_type: str) -> ExecutionGraph method stub
- [x] T016 [US1] Implement keyword-based step decomposition in `src/intelligence/planning_engine.py` — define TASK_TEMPLATES dict mapping task types (document, email, data, code, report, general) to ordered step templates; implement _extract_task_type() using keyword matching against task content
- [x] T017 [US1] Implement dependency identification in `src/intelligence/planning_engine.py` — analyze generated steps for ordering constraints (e.g., "analyze" before "generate", "read" before "process"); build edges dict; identify independent steps and populate parallelizable_groups
- [x] T018 [US1] Implement step priority assignment in `src/intelligence/planning_engine.py` — assign priorities based on dependency depth (root steps get priority 1, dependent steps get parent_priority + 1); assign estimated_duration defaults per step type
- [x] T019 [US1] Implement execution graph serialization in `src/intelligence/planning_engine.py` — save ExecutionGraph.to_json() to `/Plans/<task_filename>.graph.json` alongside existing markdown plan
- [x] T020 [US1] Integrate PlanningEngine into `src/processors/task_processor.py` — in classify_and_execute(), after classification, call PlanningEngine.decompose() for tasks without manual plan steps; guard with feature flag check (always enabled — no separate flag for planning)
- [x] T021 [US1] Implement Gold fallback in `src/processors/task_processor.py` — if PlanningEngine.decompose() raises an exception or returns None, fall back to existing Gold plan generation unchanged; log warning with error detail
- [x] T022 [US1] Add audit logging to PlanningEngine in `src/intelligence/planning_engine.py` — log `risk_scored` event with execution graph summary (step count, edge count, parallelizable groups) via operations_logger; include `src: planning_engine`

### Unit Tests for User Story 1

- [x] T023 [P] [US1] Create `tests/unit/test_execution_graph.py` — test ExecutionStep creation with valid/invalid fields; test ExecutionGraph to_json()/from_json() round-trip; test DAG validation (reject circular deps); test parallelizable group detection; test edge validation (reject unknown step_ids) — 8 tests minimum
- [x] T024 [P] [US1] Create `tests/unit/test_planning_engine.py` — test decompose() produces 3+ steps for document/email/data/report task types; test keyword extraction maps to correct task type; test dependency edges are generated correctly; test Gold fallback triggers on exception; test graph serialization writes JSON to Plans/; test audit logging emits risk_scored event — 10 tests minimum

**Checkpoint**: Planning engine generates structured execution graphs from high-level task descriptions. Gold fallback operational. 18+ new tests passing.

---

## Phase 4: User Story 2 — Self-Healing Execution (Priority: P1) MVP

**Goal**: System attempts intelligent recovery (retry, alternative strategy, partial recovery) before falling back to Gold rollback when a task step fails.

**Independent Test**: Create a complex task where step 3 of 5 fails. Verify system retries, attempts alternatives, attempts partial recovery, and only triggers Gold rollback after all strategies exhausted. Verify all recovery attempts are logged.

### Implementation for User Story 2

- [x] T025 [US2] Create SelfHealingEngine class in `src/intelligence/self_healing.py` — constructor accepts config and rollback_manager; implement recover(task_path, failed_step, execution_graph, context) -> RecoveryAttempt method stub
- [x] T026 [US2] Implement retry strategy in `src/intelligence/self_healing.py` — _attempt_retry(task_path, failed_step, context) re-executes the failed step once; return RecoveryAttempt with strategy="retry" and outcome success/failed; measure duration_ms
- [x] T027 [US2] Implement alternative strategy in `src/intelligence/self_healing.py` — _attempt_alternative(task_path, failed_step, execution_graph) looks up failed_step.alternative_step in execution graph; if defined, execute alternative step; return RecoveryAttempt with strategy="alternative"
- [x] T028 [US2] Implement partial recovery in `src/intelligence/self_healing.py` — _attempt_partial(task_path, failed_step, execution_graph) preserves all completed steps (status="completed"), marks only the failed step for manual intervention; update task frontmatter with partial_recovery status; return RecoveryAttempt with strategy="partial"
- [x] T029 [US2] Implement recovery cascade in `src/intelligence/self_healing.py` — recover() orchestrates: retry -> alternative -> partial -> Gold fallback; stop on first success; cap total attempts at MAX_RECOVERY_ATTEMPTS; return list[RecoveryAttempt] for all attempts
- [x] T030 [US2] Integrate SelfHealingEngine into `src/processors/task_processor.py` — in execution failure handler, check ENABLE_SELF_HEALING flag; if enabled, call SelfHealingEngine.recover() before invoking rollback_manager; if disabled or all recovery fails, proceed to Gold rollback unchanged
- [x] T031 [US2] Log recovery attempts in `src/intelligence/self_healing.py` — after each attempt, log self_heal_retry / self_heal_alternative / self_heal_partial event via operations_logger with timestamp, step_id, strategy, outcome, duration; include `src: self_heal`

### Unit Tests for User Story 2

- [x] T032 [P] [US2] Create `tests/unit/test_self_healing.py` — test retry succeeds on second attempt; test retry fails and triggers alternative; test alternative succeeds when defined in graph; test alternative skipped when no alternative_step; test partial recovery preserves completed steps; test full cascade exhaustion triggers Gold fallback; test MAX_RECOVERY_ATTEMPTS cap prevents infinite loops; test each strategy logs correct operation type; test ENABLE_SELF_HEALING=false skips cascade entirely — 12 tests minimum

**Checkpoint**: Self-healing cascade operational: retry -> alternative -> partial -> Gold fallback. Recovery attempts logged. 12+ new tests passing.

---

## Phase 5: User Story 3 — Predictive SLA Monitoring (Priority: P2) MVP

**Goal**: System predicts SLA breach probability for in-progress tasks using historical data and triggers early warning alerts before actual breaches occur.

**Independent Test**: Populate historical data showing 8-minute average for "document" tasks. Create an in-progress document task with 10-minute SLA running for 5 minutes. Verify system predicts breach probability > 0.7 and fires sla_prediction alert.

### Implementation for User Story 3

- [x] T033 [US3] Create SLAPredictor class in `src/intelligence/sla_predictor.py` — constructor accepts config and operations_logger; implement predict(task_path, task_type, elapsed_minutes, sla_threshold, historical_data) -> SLAPrediction
- [x] T034 [US3] Implement statistical prediction in `src/intelligence/sla_predictor.py` — compute breach probability using normal distribution approximation: P = 1 - CDF((sla_threshold - elapsed) / stdev) where CDF uses math.erf(); handle zero-variance case (return 0.0 if elapsed < mean, 1.0 if elapsed >= threshold); require minimum 3 data points for statistical prediction
- [x] T035 [US3] Implement Gold SLA fallback in `src/intelligence/sla_predictor.py` — when historical data has < 3 data points, fall back to Gold SLA estimation using operations log duration averages; return prediction with recommendation="monitor" (insufficient data)
- [x] T036 [US3] Implement recommendation logic in `src/intelligence/sla_predictor.py` — set recommendation based on probability: "on_track" (< 0.3), "monitor" (0.3-0.7), "at_risk" (> 0.7); set exceeds_threshold = probability > PREDICTION_THRESHOLD
- [x] T037 [US3] Integrate SLAPredictor into processing loop in `src/processors/task_processor.py` — guard with ENABLE_PREDICTIVE_SLA flag; for each in-progress task, call SLAPredictor.predict(); if exceeds_threshold is True, fire sla_prediction alert via operations_logger with task_id, predicted_duration, sla_threshold, probability
- [x] T038 [US3] Add audit logging to SLAPredictor in `src/intelligence/sla_predictor.py` — log sla_prediction event for every prediction (not just alerts); include `src: sla_predictor` with probability, recommendation, and task_type in detail

### Unit Tests for User Story 3

- [x] T039 [P] [US3] Create `tests/unit/test_sla_predictor.py` — test prediction with sufficient history returns valid probability; test breach probability > threshold fires alert; test breach probability < threshold does not fire alert; test zero-variance handling (no division error); test fallback when < 3 data points; test recommendation mapping (on_track/monitor/at_risk); test ENABLE_PREDICTIVE_SLA=false skips prediction; test cold start returns safe defaults — 10 tests minimum

**Checkpoint**: Predictive SLA monitoring operational. Early warnings fire before breaches. Gold SLA fallback works. 10+ new tests passing.

---

## Phase 6: User Story 4 — Dynamic Risk-Based Prioritization (Priority: P2) MVP

**Goal**: System dynamically reorders pending tasks by composite risk score (SLA risk, complexity, business impact, historical failure rate) instead of Gold's static priority ordering.

**Independent Test**: Create 3 pending tasks with priorities normal/normal/normal but different risk profiles (one high SLA risk, one high impact, one high failure history). Verify execution order follows composite risk score, not static priority.

### Implementation for User Story 4

- [x] T040 [US4] Create RiskEngine class in `src/intelligence/risk_engine.py` — constructor accepts config; implement compute_score(task_path, task_metadata, historical_data) -> RiskScore
- [x] T041 [US4] Implement composite risk score formula in `src/intelligence/risk_engine.py` — composite = (sla_risk * RISK_WEIGHT_SLA) + (complexity * RISK_WEIGHT_COMPLEXITY) + (impact * RISK_WEIGHT_IMPACT) + (failure_rate * RISK_WEIGHT_FAILURE); normalize components using COMPLEXITY_MAP and IMPACT_MAP; default failure_rate=0.0 and sla_risk=0.0 when no historical data
- [x] T042 [US4] Implement dynamic execution reordering in `src/intelligence/risk_engine.py` — reorder_tasks(task_list, historical_data) -> list sorted by composite_score descending; when all scores equal, preserve Gold static priority ordering as tiebreaker
- [x] T043 [US4] Integrate RiskEngine into `src/processors/task_processor.py` — guard with ENABLE_RISK_SCORING flag; in suggest_execution_sequence(), call RiskEngine.reorder_tasks() to replace static priority ordering when enabled; when disabled, use Gold ordering unchanged
- [x] T044 [US4] Implement Gold fallback in `src/intelligence/risk_engine.py` — when compute_score() raises exception or all scores are equal, return Gold static priority ordering; log warning with details
- [x] T045 [US4] Add audit logging to RiskEngine in `src/intelligence/risk_engine.py` — log risk_scored event after each score computation with score components; log priority_adjusted event when execution order changes from Gold ordering; include `src: risk_engine`

### Unit Tests for User Story 4

- [x] T046 [P] [US4] Create `tests/unit/test_risk_engine.py` — test score computation with all components populated; test configurable weights produce correct composite; test COMPLEXITY_MAP normalization (simple/complex/manual_review); test IMPACT_MAP normalization (low/normal/high/critical); test default values when no historical data (cold start); test reordering: highest risk first; test equal scores preserve Gold static order; test ENABLE_RISK_SCORING=false uses Gold ordering; test priority_adjusted logged on order change — 10 tests minimum

**Checkpoint**: Risk-based prioritization operational. Higher-risk tasks processed first. Gold fallback on failure/disable. 10+ new tests passing.

---

## Phase 7: User Story 5 — Learning & Optimization Engine (Priority: P3)

**Goal**: System tracks execution metrics per task type and uses historical insights to improve planning estimates, risk score accuracy, and SLA predictions over time.

**Independent Test**: Execute 10 tasks of type "document". Verify `/Learning_Data/document.json` contains aggregated metrics. Execute 11th task and verify planning engine uses historical duration estimates from learning data instead of defaults.

### Implementation for User Story 5

- [x] T047 [US5] Create LearningEngine class in `src/intelligence/learning_engine.py` — constructor accepts vault_path and config; implement record(task_result: dict) to persist metrics, query(task_type: str) -> LearningMetrics|None to retrieve, maintenance() to purge expired data
- [x] T048 [US5] Implement metrics persistence in `src/intelligence/learning_engine.py` — record() writes execution outcome (duration_ms, outcome, retry_count, recovery_method, task_type) as JSON line to `/Learning_Data/<task_type>.jsonl`; update running aggregates on same call
- [x] T049 [US5] Implement running aggregates in `src/intelligence/learning_engine.py` — after each record(), recompute LearningMetrics fields: avg_duration_ms (incremental running average), duration_variance (Welford's online algorithm), failure_count, retry_success_count, sla_breach_count; write updated aggregates to `/Learning_Data/<task_type>.meta.json`
- [x] T050 [US5] Implement data retention in `src/intelligence/learning_engine.py` — maintenance() reads each .jsonl file, removes lines older than LEARNING_WINDOW_DAYS, rewrites file; recompute aggregates from remaining data
- [x] T051 [US5] Wire learning data into PlanningEngine in `src/intelligence/planning_engine.py` — in decompose(), call LearningEngine.query(task_type); if result has total_count >= 5, use historical avg_duration_ms for step estimated_duration instead of defaults
- [x] T052 [US5] Wire learning data into RiskEngine in `src/intelligence/risk_engine.py` — in compute_score(), call LearningEngine.query(task_type); if available, use historical failure_rate instead of default 0.0
- [x] T053 [US5] Wire learning data into SLAPredictor in `src/intelligence/sla_predictor.py` — in predict(), call LearningEngine.query(task_type); use historical avg_duration_ms and duration_variance for prediction instead of operations log averages
- [x] T054 [US5] Add audit logging in `src/intelligence/learning_engine.py` — log learning_update event after each record() call with task_type, new total_count, and updated metrics summary; include `src: learning_engine`

### Unit Tests for User Story 5

- [x] T055 [P] [US5] Create `tests/unit/test_learning_engine.py` — test record() persists to correct .jsonl file; test query() returns correct aggregates; test running average computation (incremental); test variance computation (Welford's); test maintenance() purges expired data; test maintenance() preserves recent data; test derived properties (failure_rate, retry_success_rate, sla_compliance_rate); test corrupted data file handled gracefully (EC-03); test cold start returns None — 10 tests minimum

**Checkpoint**: Learning engine persists metrics. Historical data influences planning, risk, and SLA prediction. Expired data purged. 10+ new tests passing.

---

## Phase 8: User Story 6 — Safe Concurrency Control (Priority: P3)

**Goal**: System enforces configurable maximum parallel execution limit, queues excess tasks by risk score, prevents deadlocks, and enforces per-task timeouts.

**Independent Test**: Set MAX_PARALLEL_TASKS=2. Submit 5 tasks. Verify exactly 2 execute concurrently, 3 are queued in risk-score order, and no deadlocks or resource leaks occur.

### Implementation for User Story 6

- [x] T056 [US6] Create ConcurrencyController class in `src/intelligence/concurrency_controller.py` — constructor accepts config; implement acquire(task_id) -> ConcurrencySlot|None, release(slot_id), queue(task_id, risk_score), get_active_count() -> int, get_queued() -> list
- [x] T057 [US6] Implement semaphore-based task limiting in `src/intelligence/concurrency_controller.py` — use threading.Semaphore(MAX_PARALLEL_TASKS); acquire() blocks or returns None (non-blocking mode); track active slots in dict; release() decrements semaphore and clears slot
- [x] T058 [US6] Implement risk-score-based queue in `src/intelligence/concurrency_controller.py` — queue() adds task to priority queue sorted by risk_score descending; when a slot is released, automatically dequeue highest-risk task; integrate with RiskEngine for scoring
- [x] T059 [US6] Implement per-task timeout in `src/intelligence/concurrency_controller.py` — when acquire() assigns a slot, compute timeout_at = now + TASK_TIMEOUT_MINUTES; run timeout check on each loop iteration; on timeout, mark slot as timed_out, release resources, log failure
- [x] T060 [US6] Integrate ConcurrencyController into processing loop in `src/processors/task_processor.py` — before executing any task, call acquire(); if None returned (limit reached), queue the task; on task completion/failure, call release(); add timeout checking to loop iteration
- [x] T061 [US6] Add audit logging in `src/intelligence/concurrency_controller.py` — log concurrency_queued event when task is queued with task_id and queue position; include `src: concurrency_controller`

### Unit Tests for User Story 6

- [x] T062 [P] [US6] Create `tests/unit/test_concurrency_controller.py` — test acquire() succeeds within limit; test acquire() returns None at limit; test release() frees slot for next task; test queue ordering by risk score; test timeout detection marks slot as timed_out; test get_active_count() accuracy; test get_queued() returns risk-ordered list; test concurrent access safety; test concurrency_queued event logged — 10 tests minimum

**Checkpoint**: Concurrency control enforces parallel limits. Risk-score-based queuing works. Timeouts release resources. 10+ new tests passing.

---

## Phase 9: User Story 7 — Immutable Platinum Audit Trail (Priority: P3)

**Goal**: All Platinum intelligence decisions are logged with decision reasoning, action taken, and risk scores in the existing append-only operations log.

**Independent Test**: Trigger each Platinum capability. Verify `operations.log` contains entries for all 8 new Platinum operation types with correct fields including `src` decision source.

### Implementation for User Story 7

> Note: Most audit logging is implemented inline during US1-US6 (T022, T031, T038, T045, T054, T061). This phase verifies completeness and adds any missing coverage.

- [x] T063 [US7] Verify all 8 Platinum operation types are logged correctly — audit each intelligence module (planning_engine, self_healing, sla_predictor, risk_engine, learning_engine, concurrency_controller) to confirm they call operations_logger with correct `op`, `src`, and `detail` fields per FR-029
- [x] T064 [US7] Add any missing audit logging calls discovered during verification — ensure every decision path in every Platinum module produces an audit log entry; no silent code paths allowed
- [x] T065 [US7] Verify append-only integrity in `src/utils/operations_logger.py` — confirm that Platinum log entries do not modify, truncate, or interfere with existing Gold log entries; verify mixed Gold+Platinum log is valid JSON Lines

### Unit Tests for User Story 7

- [x] T066 [P] [US7] Create audit logging tests in `tests/unit/test_platinum_audit.py` — test each of 8 new operation types produces valid log entry; test `src` field present in all Platinum entries; test `detail` field contains required information (risk score, strategy, probability); test mixed Gold+Platinum log remains valid JSON Lines; test backward compatibility: Gold entries without `src` still parse correctly — 8 tests minimum

**Checkpoint**: All Platinum intelligence decisions fully auditable. 8 new operation types logged correctly. 8+ new tests passing.

---

## Phase 10: Integration & Feature Flags

**Purpose**: Wire all Platinum modules together in main processing loop and verify feature flag behavior.

- [x] T067 Wire all Platinum modules into `src/main.py` processing loop — initialize PlanningEngine, SelfHealingEngine, SLAPredictor, RiskEngine, LearningEngine, ConcurrencyController; pass to task_processor; connect inter-module data flows (learning -> planning/risk/sla)
- [x] T068 [P] Verify ENABLE_SELF_HEALING=false in `src/processors/task_processor.py` — confirm self-healing cascade is skipped entirely; failures go directly to Gold rollback; no Platinum recovery attempts logged
- [x] T069 [P] Verify ENABLE_PREDICTIVE_SLA=false in `src/processors/task_processor.py` — confirm SLA prediction loop is skipped; no sla_prediction events logged; Gold reactive breach detection still works
- [x] T070 [P] Verify ENABLE_RISK_SCORING=false in `src/processors/task_processor.py` — confirm Gold static priority ordering is used; no risk_scored or priority_adjusted events logged
- [x] T071 Verify Gold fallback: run all 205 existing Gold tests with ALL Platinum features disabled (ENABLE_SELF_HEALING=false, ENABLE_PREDICTIVE_SLA=false, ENABLE_RISK_SCORING=false) — confirm 205/205 pass with 0 failures

**Checkpoint**: All modules wired. Feature flags toggle behavior correctly. Gold regression verified.

---

## Phase 11: Integration Tests

**Purpose**: End-to-end verification of each user story and full Platinum workflow.

- [x] T072 [P] [US1] Integration test: intelligent planning workflow in `tests/integration/test_platinum_workflow.py` — create task with "Organize quarterly report from raw data files" in Needs_Action; run processing; verify execution graph in Plans/ with 3+ steps, dependency edges, and per-step priorities (SC-001, SC-002)
- [x] T073 [P] [US2] Integration test: self-healing recovery cascade in `tests/integration/test_platinum_workflow.py` — create complex task where step 3 fails; mock failure; verify retry attempted first, then alternative (if defined), then partial; verify Gold rollback only after all strategies exhausted; verify all recovery attempts in operations.log (SC-003, SC-004)
- [x] T074 [P] [US3] Integration test: predictive SLA monitoring in `tests/integration/test_platinum_workflow.py` — populate historical data (avg 8min for "document"); create in-progress document task at 5min elapsed with 10min SLA; run prediction; verify sla_prediction event logged with probability; verify alert fires when probability > threshold (SC-005, SC-006)
- [x] T075 [P] [US4] Integration test: risk-based priority reordering in `tests/integration/test_platinum_workflow.py` — create 3 tasks: high SLA risk + normal priority, low SLA risk + critical priority, medium SLA risk + normal priority; run risk scoring; verify execution order follows composite risk score not static priority (SC-007, SC-008)
- [x] T076 [P] [US5] Integration test: learning engine lifecycle in `tests/integration/test_platinum_workflow.py` — execute 5 tasks of type "document"; verify Learning_Data/document.jsonl and document.meta.json exist with correct aggregates; execute 6th task; verify planning engine uses historical duration estimate (SC-009, SC-010)
- [x] T077 [P] [US6] Integration test: concurrency control in `tests/integration/test_platinum_workflow.py` — set MAX_PARALLEL_TASKS=2; submit 4 tasks; verify only 2 active simultaneously; verify remaining 2 queued in risk-score order; verify timeout mechanism releases resources (SC-011, SC-012)
- [x] T078 [US7] Integration test: full Platinum workflow in `tests/integration/test_platinum_workflow.py` — end-to-end: task arrives -> planning engine decomposes -> risk engine prioritizes -> concurrency controller admits -> execution with self-healing -> learning engine records -> SLA predictor monitors -> all decisions in audit log (SC-013, SC-015)
- [x] T079 Gold regression: run full test suite and verify 205 existing tests + all new Platinum tests pass with 0 failures (SC-014)

**Checkpoint**: All 7 user stories verified end-to-end. Full Platinum workflow passing. Gold regression confirmed.

---

## Phase 12: Edge Cases

**Purpose**: Verify system handles all 8 spec-defined edge cases gracefully.

- [x] T080 [P] Edge case EC-01 (empty task) in `tests/integration/test_platinum_workflow.py` — task with no content body falls back to Gold plan generator; logs warning; no crash
- [x] T081 [P] Edge case EC-02 (cascading failures) in `tests/integration/test_platinum_workflow.py` — retry succeeds but next step also fails; system re-enters recovery cascade for new failure; total attempts capped at MAX_RECOVERY_ATTEMPTS per task
- [x] T082 [P] Edge case EC-03 (corrupted learning data) in `tests/integration/test_platinum_workflow.py` — corrupt Learning_Data file; system logs error, falls back to defaults, recreates data on next write
- [x] T083 [P] Edge case EC-04 (critical task preemption) in `tests/integration/test_platinum_workflow.py` — all slots occupied, critical task arrives; placed at front of queue (highest risk score)
- [x] T084 [P] Edge case EC-05 (zero variance) in `tests/integration/test_platinum_workflow.py` — all historical durations identical; prediction handles zero variance without division error; returns deterministic estimate
- [x] T085 [P] Edge case EC-06 (missing risk fields) in `tests/integration/test_platinum_workflow.py` — task missing priority and complexity frontmatter; system uses defaults (normal/simple) and computes valid risk score
- [x] T086 [P] Edge case EC-07 (cold start) in `tests/integration/test_platinum_workflow.py` — no historical data; all Platinum modules use safe defaults; system functions identically to Gold
- [x] T087 [P] Edge case EC-08 (file conflict) in `tests/integration/test_platinum_workflow.py` — two concurrent tasks modify same output file; concurrency control serializes conflicting tasks

**Checkpoint**: All 8 edge cases handled gracefully. No crashes, no undefined behavior.

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, dashboard, notifications, and cleanup.

- [x] T088 [P] Update `src/utils/dashboard_updater.py` with Platinum metrics — add retry success rate (last 24h), predictive alerts issued (last 24h), risk score distribution (high/medium/low), learning engine data points collected
- [x] T089 [P] Update `src/notifications/notifier.py` with Platinum alert types — add predictive SLA warning, self-healing recovery attempt, concurrency limit reached to alert type enum
- [x] T090 [P] Update `.env.example` with final documentation — ensure all 12 Platinum parameters have clear descriptions, default values, and usage notes
- [x] T091 Update README.md for Platinum Tier submission — add architecture overview, 7 capabilities summary, configuration guide, test results

**Checkpoint**: Dashboard displays Platinum metrics. Notifications cover all Platinum events. Documentation complete.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────── No dependencies (start immediately)
  │
Phase 2: Foundational ──────────────── Depends on Phase 1 (T001 for package)
  │                                     BLOCKS all user stories
  │
  ├── Phase 3: US1 Planning (P1) ───── Depends on Phase 2
  │     │
  ├── Phase 4: US2 Self-Healing (P1) ─ Depends on Phase 2 + T007 (ExecutionGraph for alternatives)
  │     │
  ├── Phase 5: US3 SLA Prediction ──── Depends on Phase 2
  │     │
  ├── Phase 6: US4 Risk Scoring ────── Depends on Phase 2
  │     │
  ├── Phase 7: US5 Learning Engine ─── Depends on Phase 2 + T015,T033,T040 (feeds into P1,P3,P4)
  │     │
  ├── Phase 8: US6 Concurrency ─────── Depends on Phase 2 + T040 (risk-based queue)
  │     │
  └── Phase 9: US7 Audit Trail ─────── Depends on audit tasks in US1-US6
        │
Phase 10: Integration ──────────────── Depends on all user story phases
  │
Phase 11: Integration Tests ────────── Depends on Phase 10
  │
Phase 12: Edge Cases ───────────────── Depends on Phase 10
  │
Phase 13: Polish ───────────────────── Depends on Phase 11 + 12
```

### User Story Dependencies

- **US1 (Planning)**: Independent — can start immediately after Phase 2
- **US2 (Self-Healing)**: Needs ExecutionGraph from US1 (T007) for alternative step lookup
- **US3 (SLA Prediction)**: Independent — can start after Phase 2; enhanced by US5 (learning data)
- **US4 (Risk Scoring)**: Independent — can start after Phase 2; enhanced by US5 (failure rates)
- **US5 (Learning Engine)**: Needs US1+US3+US4 complete to wire data feeds
- **US6 (Concurrency)**: Needs US4 for risk-score-based queuing
- **US7 (Audit Trail)**: Cross-cutting; verification after US1-US6

### Parallel Opportunities

**After Phase 2 completes, these can run in parallel:**
- US1 (Planning) + US3 (SLA Prediction) + US4 (Risk Scoring) — no cross-dependencies
- US2 (Self-Healing) can start in parallel but needs T007 from US1

**Within each User Story, [P] tasks can run in parallel:**
- Data model tasks (T006-T012) are all independent
- Unit test files for different stories are all independent
- Integration tests (T072-T078) are all independent (except T078 which depends on all others)

---

## Parallel Example: User Story 1

```bash
# After Phase 2 completes, launch US1 implementation:
Task T015: "Create PlanningEngine class in src/intelligence/planning_engine.py"
# Then sequentially: T016 -> T017 -> T018 -> T019 -> T020 -> T021 -> T022

# In parallel with US1 implementation, launch US1 unit tests:
Task T023: "Unit tests for ExecutionGraph in tests/unit/test_execution_graph.py"
Task T024: "Unit tests for PlanningEngine in tests/unit/test_planning_engine.py"
```

## Parallel Example: After Phase 10

```bash
# All integration tests can run in parallel:
Task T072: "Integration test: planning workflow"
Task T073: "Integration test: self-healing cascade"
Task T074: "Integration test: predictive SLA"
Task T075: "Integration test: risk-based priority"
Task T076: "Integration test: learning engine lifecycle"
Task T077: "Integration test: concurrency control"

# All edge case tests can run in parallel:
Task T080-T087: "Edge cases EC-01 through EC-08"
```

---

## Implementation Strategy

### MVP First (US1 + US2 — Core Platinum)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T014)
3. Complete Phase 3: US1 Planning (T015-T024)
4. Complete Phase 4: US2 Self-Healing (T025-T032)
5. **STOP and VALIDATE**: Run all tests (205 Gold + ~40 Platinum)
6. Deploy/demo Platinum MVP with intelligent planning + self-healing

### Incremental Delivery

1. **Setup + Foundation** -> All data models ready, Gold stable
2. **+ US1 Planning** -> Tasks auto-decompose into execution graphs (MVP!)
3. **+ US2 Self-Healing** -> Failed steps recover before rollback (MVP!)
4. **+ US3 SLA Prediction** -> Early warning alerts before breaches
5. **+ US4 Risk Scoring** -> Dynamic priority ordering
6. **+ US5 Learning Engine** -> Historical data improves all modules
7. **+ US6 Concurrency** -> Parallel execution with limits
8. **+ US7 Audit Trail** -> Full traceability verified
9. **Integration Tests + Edge Cases** -> Complete verification
10. **Polish** -> Dashboard, notifications, documentation

### Task Count by Story

| Story | Implementation | Unit Tests | Integration | Edge Cases | Total |
|-------|---------------|------------|-------------|------------|-------|
| Setup (Phase 1) | 5 | — | — | — | 5 |
| Foundational (Phase 2) | 9 | — | — | — | 9 |
| US1: Planning | 8 | 2 | 1 | 1 | 12 |
| US2: Self-Healing | 7 | 1 | 1 | 2 | 11 |
| US3: SLA Prediction | 6 | 1 | 1 | 1 | 9 |
| US4: Risk Scoring | 6 | 1 | 1 | 1 | 9 |
| US5: Learning Engine | 8 | 1 | 1 | 1 | 11 |
| US6: Concurrency | 6 | 1 | 1 | 2 | 10 |
| US7: Audit Trail | 3 | 1 | 1 | — | 5 |
| Integration & Flags | 5 | — | — | — | 5 |
| Regression & E2E | — | — | 1 | — | 1 |
| Polish | 4 | — | — | — | 4 |
| **Totals** | **67** | **8** | **8** | **8** | **91** |

---

## Status

91/91 tasks complete (100%) | 205 Gold tests passing | 148 Platinum tests passing | 353 total tests

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable at its checkpoint
- Commit after each task or logical group
- Gold regression (T071, T079) is a critical gate — must pass before proceeding
- All Platinum modules live in `src/intelligence/` to minimize Gold code changes
- Feature flags allow disabling any Platinum feature individually
