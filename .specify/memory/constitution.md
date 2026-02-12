<!--
  ============================================================
  SYNC IMPACT REPORT
  ============================================================
  Version change: 3.0.0 → 4.0.0 (MAJOR)
  Bump rationale: Platinum Tier introduces a new Intelligence
    Layer (Section IX) with 7 capabilities (P1-P7) that
    fundamentally change the system from rule-based automation
    to adaptive, self-planning, self-healing autonomous
    execution. This constitutes a backward-incompatible
    governance change: new decision-making paradigms
    (predictive SLA, risk-based prioritization, learning
    engine) override Gold's static priority and fixed-gate
    model.

  Modified principles:
    - I. Functional Foundation Layer: added Platinum self-
      healing execution, intelligent retry before rollback,
      concurrency control requirements
    - II. Vault-Centric Architecture: added /Learning_Data/
      folder for historical execution metrics storage
    - IV. Reasoning Layer: upgraded from static plan
      generation to intelligent task decomposition with
      dependency graph and execution graph output
    - V. Action Layer: renamed to "Platinum Orchestration";
      added self-healing recovery cascade (retry → alternative
      → partial recovery → Gold rollback), predictive risk
      scoring, dynamic priority adjustment

  Added sections:
    - IX. Platinum Intelligence Layer (new — P1 through P7)
    - Platinum-specific SLA and metrics extensions
    - Platinum completion criteria in Governance

  Removed sections: None (full backward compatibility)

  Resolved TODOs from Gold Tier:
    - SLA_SIMPLE_MINUTES: resolved to 2 minutes (Gold config)
    - SLA_COMPLEX_MINUTES: resolved to 10 minutes (Gold config)
    - UPTIME_HOURS: resolved to 8 hours
    - NOTIFICATION_CHANNEL: resolved to webhook (Gold impl)

  Templates requiring updates:
    - .specify/templates/plan-template.md ⚠ pending
      (Constitution Check should reference Platinum
      intelligence gates and risk scoring)
    - .specify/templates/spec-template.md ✅ No update needed
      (generic user story format remains compatible)
    - .specify/templates/tasks-template.md ⚠ pending
      (phase structure should account for intelligence layer,
      learning engine, and concurrency control tasks)
    - .specify/templates/commands/ ✅ No update needed
    - README.md ⚠ pending (still references Gold Tier;
      must be updated for Platinum submission)

  Deferred items:
    - TODO(PREDICTION_THRESHOLD): SLA breach prediction
      probability threshold (default 0.7) requires tuning
      with real execution data
    - TODO(MAX_PARALLEL_TASKS): Safe concurrency limit
      requires benchmarking under load
    - TODO(LEARNING_WINDOW_DAYS): Historical data window
      for learning engine requires experimentation
  ============================================================
-->
# Autonomous Employee Constitution

## Core Principles

### I. Functional Foundation Layer

- Claude Code and Obsidian Vault integration MUST be
  operational and verified before any task processing begins.
- Watcher scripts MUST be running and capable of detecting
  external input (Gmail, File System, or API webhook).
- Silver Baseline: The system MUST auto-detect new task types
  beyond plain markdown (e.g., email forwards, file drops)
  and route them to the appropriate Vault folder.
- Silver Baseline: Error handling MUST log all watcher and
  Claude Code failures with timestamps and error categories
  so that issues are traceable without manual debugging.
- Gold Upgrade: The system MUST support multi-step task
  orchestration, executing sequential and parallel sub-steps
  within a single task lifecycle.
- Gold Upgrade: A health-check heartbeat MUST run every loop
  iteration, verifying that all critical components (watchers,
  processor, mover, dashboard) are responsive. Failures MUST
  be logged and surfaced on the dashboard.
- Gold Upgrade: When an external service dependency is
  unavailable, the system MUST degrade gracefully — queueing
  affected tasks for retry rather than failing the entire
  processing loop.
- Platinum Upgrade: Before triggering Gold rollback, the
  system MUST attempt a self-healing recovery cascade:
  (1) retry the failed step, (2) attempt an alternative
  strategy, (3) attempt partial recovery, (4) fall back to
  Gold rollback. All recovery attempts MUST be logged. No
  silent failures are permitted.
- Platinum Upgrade: The system MUST respect a configurable
  maximum parallel execution limit
  (`MAX_PARALLEL_TASKS`). Concurrent task execution MUST
  NOT exceed this limit. The system MUST prevent deadlocks
  and resource overload under concurrent processing.

### II. Vault-Centric Architecture

- Obsidian Vault is the single source of truth for all task
  state. The canonical folder structure is:
  - `/Needs_Action/` — New tasks awaiting processing
  - `/In_Progress/` — Tasks currently being executed
  - `/Done/` — Completed tasks
  - `/Plans/` — Claude-generated plans and reasoning artifacts
  - `/Rollback_Archive/` — Pre-execution state snapshots
    for rollback capability **(Gold Tier)**
  - `/Learning_Data/` — Historical execution metrics and
    learning engine data **(Platinum Tier)**
- `Dashboard.md` MUST reflect current task counts, SLA
  compliance, predictive risk scores, and recent activity.
  `Company_Handbook.md` defines behavioral rules.
- Silver Baseline: The system MUST auto-move tasks between
  folders based on status changes. When a task is marked
  complete, it MUST be moved to `/Done/` without manual
  intervention. When processing begins, the task MUST be
  moved to `/In_Progress/`.
- Gold Upgrade: Before executing any task classified as
  complex, the system MUST snapshot the task file and any
  associated output files into `/Rollback_Archive/` with a
  timestamp prefix. This enables automatic rollback on
  failure.
- Gold Upgrade: Each task file MUST carry a `version:` field
  in its frontmatter, incremented on every status change or
  re-classification, providing a traceable state history.
- Platinum Upgrade: Execution metrics (duration, outcome,
  retry count, recovery method) MUST be persisted to
  `/Learning_Data/` after every task completion or failure,
  enabling the Learning Engine to derive historical insights.

### III. Perception Layer (Watchers)

- At least one Watcher script MUST be operational at all times
  during active use (Gmail Watcher, File System Watcher, or
  API Webhook Watcher).
- Watchers MUST convert detected input into `.md` task files
  and save them to `/Needs_Action/`.
- Silver Baseline: Watchers MUST support real-time recognition
  of incoming tasks (polling interval <= 30 seconds or
  event-driven where supported).
- Silver Baseline: Watchers MUST categorize detected files by
  type (email, document, image, data file) and tag the
  resulting task markdown with a `type:` front-matter field.
- Gold Upgrade: Watchers MUST support webhook-based and API
  event-source inputs in addition to file and email watchers.
  New source types MUST be registered in
  `Company_Handbook.md` before activation.
- Gold Upgrade: Watchers MUST assign a `priority:` field
  (critical, high, normal, low) to incoming tasks based on
  configurable rules (source type, keywords, sender). Tasks
  with `priority: critical` MUST be routed for immediate
  processing ahead of the normal queue.
- Gold Upgrade: Watchers MUST trigger a dashboard alert when
  the incoming task rate exceeds a configurable threshold,
  indicating potential flooding or anomalous input.

### IV. Reasoning Layer (Intelligent Planning)

- Claude Code serves as the AI reasoning engine ("brain").
- Claude Code MUST read tasks from `/Needs_Action/`, generate
  plans with checkbox steps, and write them to `/Plans/`.
- The reasoning loop MUST run continuously or on-demand via
  the `--process` flag.
- Silver Baseline: Claude Code MUST suggest task execution
  sequences when multiple tasks are pending, prioritizing by
  urgency and dependency order.
- Silver Baseline: For simple, well-defined tasks (single-step,
  no external dependencies), Claude Code MUST trigger partial
  automated execution and record the outcome in the task file.
- Gold Upgrade: Claude Code MUST support conditional branching
  workflows — selecting different execution paths based on
  task attributes (type, priority, complexity, source). Branch
  conditions MUST be defined in plan steps and logged.
- Gold Upgrade: Claude Code MUST resolve dependency graphs
  when processing multi-step plans, ensuring prerequisite
  steps complete before dependent steps begin.
- Gold Upgrade: Multi-step plan execution MUST use
  checkpoints. After each step, the system MUST record
  success/failure in the task's `## Execution Log`. If a
  step fails, remaining steps MUST NOT execute unless an
  explicit retry or override is issued.
- Platinum Upgrade: The Intelligent Planning Engine MUST
  convert high-level requests into structured execution plans
  by: (1) breaking tasks into ordered sub-steps,
  (2) identifying dependencies between steps,
  (3) assigning execution priority per step, and
  (4) producing a structured execution graph. The execution
  graph MUST be stored in the task's plan file.
- Platinum Upgrade: The system MUST dynamically re-prioritize
  pending tasks based on a composite risk score computed from:
  SLA breach probability, task complexity, business impact
  weight, and historical failure rate. Execution order MUST
  adapt on every processing loop iteration.

### V. Action Layer (Platinum Orchestration)

- Actions MUST be scoped to Vault file operations and plan
  generation by default. External API calls or cloud
  operations require explicit authorization.
- Silver Baseline: Tasks flagged as complete MUST be
  auto-moved to `/Done/` by the orchestrator.
- Silver Baseline: The system MUST trigger partial plan
  execution for tasks classified as "simple" (few steps,
  deterministic outcome, no credentials required).
- Silver Baseline: The system MUST generate interim dashboards
  with progress metrics including: tasks pending, in-progress,
  completed, average completion time, and error rate.
- Gold Upgrade: The system MUST support execution of complex
  multi-step tasks when `AUTO_EXECUTE_COMPLEX` is enabled and
  the task passes all Gold Tier automation gates (see
  Section VI).
- Gold Upgrade: External API or cloud service integration
  MUST be gated by a permission allowlist in `.env`
  (`ALLOWED_EXTERNAL_SERVICES`). Any operation targeting a
  service not on the allowlist MUST be blocked and logged.
- Gold Upgrade: On task execution failure, the system MUST
  attempt automatic recovery:
  1. Log the failure with full context (step, error, state).
  2. Restore pre-execution state from `/Rollback_Archive/`.
  3. Mark the task as `status: failed_rollback` in frontmatter.
  4. Surface the failure on the dashboard with remediation
     guidance.
- Gold Upgrade: Real-time notifications MUST be emitted for
  task status transitions (pending -> in_progress -> done/failed)
  via webhook notification channel.
- Platinum Upgrade: On task execution failure, the system MUST
  execute a self-healing cascade BEFORE triggering Gold
  rollback:
  1. **Retry**: Re-execute the failed step (max 1 retry).
  2. **Alternative**: Attempt an alternative execution
     strategy if defined in the plan.
  3. **Partial Recovery**: Attempt to salvage completed steps
     and mark only the failed step for manual intervention.
  4. **Fallback**: If all recovery attempts fail, invoke Gold
     rollback mechanism.
  All recovery attempts MUST be logged with: timestamp,
  strategy attempted, outcome, and duration.
- Platinum Upgrade: The system MUST use predictive SLA
  monitoring to trigger early warnings when the probability
  of SLA breach exceeds a configurable threshold
  (`PREDICTION_THRESHOLD`, default 0.7). Predictive alerts
  MUST be logged as `sla_prediction` events in the
  operations log and surfaced on the dashboard.
- Platinum Upgrade: The Learning Engine MUST track and persist:
  average execution time per task type, failure frequency per
  operation, retry success rate, and SLA compliance rate.
  Historical insights MUST influence future planning
  (estimated step durations) and prioritization (risk scores).

## VI. Gold Tier Automation Gates

*These gates extend the Silver Tier three-gate classification
system. A task MUST pass ALL applicable gates before
auto-execution.*

### Gate 1: Step Count (inherited, extended)

- Simple tasks: <= 5 actionable steps (Silver baseline).
- Complex tasks: <= 15 actionable steps with checkpoint
  support **(Gold extension)**.
- Tasks exceeding 15 steps MUST be flagged for manual
  review and MUST NOT auto-execute.

### Gate 2: Credential Check (inherited)

- Task content and plan steps MUST NOT reference credentials,
  secrets, tokens, API keys, SSH keys, or `.env` files.
- Any credential reference MUST block auto-execution and
  trigger a credential scan alert.

### Gate 3: Determinism Check (inherited, extended)

- Simple tasks: file-system-only operations (Silver baseline).
- Complex tasks: MAY include pre-approved external service
  calls if the target service is on the `ALLOWED_EXTERNAL_SERVICES`
  allowlist **(Gold extension)**.
- Operations involving non-deterministic outcomes (e.g.,
  LLM-generated content, third-party API responses) MUST
  include validation checkpoints in the plan.

### Gate 4: Permission Gate (Gold Tier)

- File operations: ALLOWED by default within the Vault.
- Network/API operations: ALLOWED only if the target service
  is listed in `ALLOWED_EXTERNAL_SERVICES` in `.env`.
- Destructive operations (file deletion, overwrite of
  existing content): MUST require explicit `destructive: true`
  flag in the task frontmatter and MUST snapshot to
  `/Rollback_Archive/` before execution.
- Operations outside the Vault directory tree MUST be blocked.

### Gate 5: SLA Feasibility Gate (Gold Tier)

- Before execution, the system MUST estimate whether the task
  can complete within the applicable SLA threshold.
- If estimated duration exceeds the SLA by more than 50%, the
  task MUST be flagged for manual review.
- Estimation MAY use historical average completion times from
  the operations log.
- Platinum Extension: Estimation MUST use the Learning Engine
  historical data when available, falling back to operations
  log averages when learning data is insufficient.

### Gate 6: Rollback Readiness Gate (Gold Tier)

- Before executing any complex task, the system MUST verify
  that a rollback snapshot has been created in
  `/Rollback_Archive/`.
- If snapshot creation fails, execution MUST NOT proceed.

## Development Workflow

- Environment setup MUST use Python 3.12+ with dependencies
  managed via `pyproject.toml` or `requirements.txt` and
  installed in a virtual environment (`.venv/`).
- Watcher development follows a detect-convert-save pipeline:
  detect external input, convert to `.md`, save to Vault.
- All watcher runs MUST produce structured logs (JSON format
  preferred) capturing: timestamp, event type, source, and
  outcome (success/failure with reason).
- Task execution logs MUST be appended to each task file as a
  `## Execution Log` section with timestamped entries.
- Gold Upgrade: Multi-step execution MUST record per-step
  outcomes in the execution log, not just a single final
  result.
- Platinum Upgrade: Self-healing recovery attempts MUST be
  recorded in the execution log with strategy name, attempt
  number, and outcome.
- Platinum Upgrade: The Learning Engine MUST persist metrics
  to `/Learning_Data/` in JSON format after each task
  lifecycle completes.
- Continuous monitoring of the Vault is recommended during
  active development to verify folder state consistency.

## Security & Compliance

- Secrets and API credentials MUST never be stored in the
  Vault or committed to version control.
- All API keys MUST be stored in `.env` files and `.env` MUST
  be listed in `.gitignore`.
- The system MUST auto-check for credentials and sensitive
  file patterns (`.pem`, `.key`, tokens) before committing
  and reject commits containing them.
- Operational scope MUST remain local-only by default. Any
  external cloud connections require explicit user
  authorization and documentation in `Company_Handbook.md`.
- Gold Upgrade: Pre-commit hooks MUST scan staged files for
  credential patterns. Runtime scanning MUST run every loop
  iteration when `CREDENTIAL_SCAN_ENABLED=true`.
- Gold Upgrade: The operations audit log (`operations.log`)
  MUST be append-only. The system MUST NOT overwrite, truncate,
  or delete entries. Log integrity SHOULD be verifiable via
  line-count checkpoints recorded in Dashboard.md.
- Gold Upgrade: Permission-based gating MUST apply to all
  categories of operations:
  - **File operations**: ALLOWED within Vault by default.
  - **Network operations**: BLOCKED unless target is on the
    `ALLOWED_EXTERNAL_SERVICES` allowlist.
  - **API operations**: BLOCKED unless explicitly enabled via
    `AUTO_EXECUTE_COMPLEX=true` and service is allowlisted.
  - **Destructive operations**: BLOCKED unless `destructive:
    true` is set in task frontmatter AND rollback snapshot
    exists.

## VII. Success Criteria & SLA

### SLA Thresholds

- Simple task completion: MUST complete within 2 minutes
  (`SLA_SIMPLE_MINUTES`) from classification to
  `status: done`.
- Complex task completion: MUST complete within 10 minutes
  (`SLA_COMPLEX_MINUTES`) from classification to
  `status: done`.
- SLA breaches MUST be logged as `sla_breach` events in the
  operations log and surfaced on the dashboard.
- Platinum Extension: Predictive SLA alerts MUST fire when
  breach probability exceeds `PREDICTION_THRESHOLD` (default
  0.7), logged as `sla_prediction` events BEFORE the breach
  occurs.

### Operational Uptime

- The system MUST maintain continuous operation for at least
  8 hours without manual restart when running in `--loop`
  mode.
- Crashes or unhandled exceptions MUST be caught at the loop
  level, logged, and the loop MUST continue processing
  remaining tasks.

### Safety Detection

- Unsafe or blocked operations MUST be detected and rejected
  BEFORE execution begins (pre-execution gate check).
- No operation MUST bypass the gate system. If gates cannot
  be evaluated (e.g., missing frontmatter), the task MUST
  default to `complex` classification and require manual
  review.

### Tracked Metrics

- **Task throughput**: Number of tasks completed per hour.
- **Error rate**: Percentage of tasks that fail execution
  (target: < 5%).
- **Rollback incidents**: Count of automatic rollbacks
  triggered per day (target: < 2).
- **SLA compliance**: Percentage of tasks completed within
  SLA thresholds (target: > 90%).
- **Classification accuracy**: Ratio of correctly classified
  simple vs. complex tasks (measured by post-execution
  review).
- **Platinum — Retry success rate**: Percentage of failed
  steps recovered via self-healing without rollback
  (target: > 30%).
- **Platinum — Prediction accuracy**: Percentage of
  predictive SLA alerts that correctly identified an
  impending breach (target: > 70%).
- **Platinum — Learning utilization**: Percentage of task
  prioritization decisions influenced by historical data
  (target: > 50% after 24h of operation).

## VIII. Audit & Observability

### Immutable Operations Log

- All executed tasks, movements, classifications, and
  execution outcomes MUST be recorded in `operations.log`
  in JSON Lines format (one entry per line).
- Each entry MUST include: `ts` (ISO timestamp), `op`
  (operation type), `file` (task filename), `src` (source
  folder), `dst` (destination folder or null), `outcome`
  (success/failed/flagged), `detail` (context string).
- The log MUST be append-only. Truncation or deletion of
  log entries is a governance violation.
- Platinum Extension: All Platinum intelligence decisions
  MUST be logged with: timestamp, task ID, decision reason,
  action taken, and risk score (if applicable). New operation
  types: `sla_prediction`, `risk_scored`, `self_heal_retry`,
  `self_heal_alternative`, `self_heal_partial`,
  `learning_update`, `priority_adjusted`.

### Dashboard Metrics

- `Dashboard.md` MUST track and display:
  - Pending task count
  - In-progress task count
  - Completed task count (today and all-time)
  - Average task completion time (last 24 hours)
  - Error rate (last 24 hours)
  - Rollback incidents (last 24 hours)
  - SLA compliance percentage (last 24 hours)
  - Plans generated count
  - Watcher status (active/inactive per watcher type)
  - Last updated timestamp
  - **Platinum**: Retry success rate (last 24 hours)
  - **Platinum**: Predictive alerts issued (last 24 hours)
  - **Platinum**: Risk score distribution (high/medium/low)
  - **Platinum**: Learning engine data points collected

### Manual Review & Override

- Tasks classified as `complex` with `priority: critical`
  MUST be flagged for optional manual review before
  auto-execution proceeds (if `AUTO_EXECUTE_COMPLEX=true`).
- A human operator MAY override any gate by setting
  `override: true` in the task frontmatter. Overrides MUST
  be logged with the operator's identity and justification
  in the operations log.
- Override history MUST be preserved in the task's
  `## Execution Log` section.

### Alerting

- The system MUST emit alerts (via dashboard and
  notification channel) for:
  - Task execution failure
  - SLA breach
  - Credential pattern detected
  - Rollback triggered
  - Watcher failure or unresponsive heartbeat
  - Anomalous incoming task rate
  - **Platinum**: Predictive SLA breach warning
  - **Platinum**: Self-healing recovery attempt
  - **Platinum**: Concurrency limit reached
- Alert severity levels: `critical`, `warning`, `info`.
- Critical alerts MUST be surfaced immediately; warning and
  info alerts MUST appear on the next dashboard refresh.

## IX. Platinum Intelligence Layer

*This section defines the 7 core capabilities that elevate
the system from rule-based automation (Gold) to intelligent,
adaptive autonomy (Platinum). All capabilities are additive;
Gold Tier execution remains fully operational as the
foundation.*

### P1. Intelligent Task Planning

- The system MUST convert high-level user requests into
  structured execution plans without manual step definition.
- Plan generation MUST: (1) break tasks into ordered
  sub-steps, (2) identify dependencies between steps,
  (3) assign execution priority to each step, and
  (4) produce a structured execution graph.
- The execution graph MUST be serializable (JSON) and stored
  alongside the plan in `/Plans/`.
- When dependencies exist, the system MUST enforce execution
  order. Independent steps MAY execute concurrently if
  `MAX_PARALLEL_TASKS` allows.

### P2. Self-Healing Execution

- Before triggering Gold rollback, the system MUST attempt
  intelligent recovery through a defined cascade:
  1. **Retry**: Re-execute the failed step (1 attempt).
  2. **Alternative Strategy**: If the plan defines an
     alternative path for the failed step, attempt it.
  3. **Partial Recovery**: Salvage successfully completed
     steps and isolate only the failed step for manual
     intervention, avoiding full rollback.
  4. **Gold Fallback**: If all recovery attempts fail,
     invoke the Gold rollback mechanism (snapshot restore,
     `status: failed_rollback`).
- Every recovery attempt MUST be logged with: timestamp,
  step identifier, strategy name, outcome, and duration.
- No silent failures: if a step fails and no recovery
  succeeds, the failure MUST be surfaced via alert and
  dashboard.

### P3. Predictive SLA Monitoring

- The system MUST use historical execution duration data
  (from the Learning Engine) to predict the probability of
  SLA breach for each in-progress task.
- If predicted breach probability exceeds
  `PREDICTION_THRESHOLD` (default: 0.7), the system MUST
  trigger an early warning alert BEFORE the actual breach
  occurs.
- Predictive alerts MUST be logged as `sla_prediction`
  events in the operations log with: task ID, predicted
  duration, threshold, probability, and recommendation.
- Prediction MUST run on every processing loop iteration for
  all in-progress tasks.

### P4. Dynamic Risk-Based Prioritization

- Task priority MUST be computed dynamically using a
  composite risk score derived from:
  - **SLA risk probability**: likelihood of breaching SLA
    (from P3 predictions)
  - **Task complexity**: simple=1, complex=2, manual_review=3
  - **Business impact weight**: derived from `priority:`
    field (critical=4, high=3, normal=2, low=1)
  - **Historical failure rate**: percentage of similar tasks
    that failed in historical data
- The composite score formula:
  `risk_score = (sla_risk * 0.3) + (complexity * 0.2) +
  (impact * 0.3) + (failure_rate * 0.2)`
- Execution order MUST be re-computed on every processing
  loop iteration. Tasks with higher risk scores MUST be
  processed first.
- Priority adjustments MUST be logged as `priority_adjusted`
  events in the operations log.

### P5. Learning & Optimization Engine

- The system MUST track and persist the following metrics
  per task type and operation:
  - Average execution time
  - Failure frequency
  - Retry success rate
  - SLA compliance rate
- Metrics MUST be stored in `/Learning_Data/` in JSON format
  with a configurable retention window
  (`LEARNING_WINDOW_DAYS`, default: 30).
- Historical insights MUST influence:
  - **Planning**: Estimated step durations in execution
    graphs (P1).
  - **Prioritization**: Historical failure rates in risk
    score computation (P4).
  - **SLA Prediction**: Duration estimates for breach
    probability calculation (P3).
- The Learning Engine MUST update its data after every task
  completion or failure, logged as `learning_update` events.

### P6. Safe Concurrency Control

- The system MUST respect a configurable maximum parallel
  execution limit (`MAX_PARALLEL_TASKS`, default: 3).
- When the concurrency limit is reached, additional tasks
  MUST be queued and processed in risk-score order (P4).
- The system MUST prevent deadlocks by: (1) enforcing a
  timeout on each concurrent task, (2) releasing resources
  on timeout, and (3) logging the timeout as a failure.
- Resource overload MUST be detected by monitoring system
  metrics (CPU, memory) if available, or by tracking active
  task count against the configured limit.
- Concurrency limit reached events MUST be logged and
  surfaced as `warning` severity alerts.

### P7. Immutable Audit Logging (Platinum Extension)

- All Platinum intelligence decisions MUST be logged in the
  same `operations.log` file used by Gold, maintaining a
  single audit trail.
- Each Platinum log entry MUST include:
  - `ts`: ISO timestamp
  - `op`: Operation type (see new types below)
  - `file`: Task filename
  - `src`: Decision source (e.g., `planning_engine`,
    `risk_engine`, `self_heal`, `learning_engine`)
  - `outcome`: success/failed/flagged
  - `detail`: Context string including decision reason,
    action taken, and risk score where applicable
- New Platinum operation types:
  - `sla_prediction` — Predictive SLA breach alert
  - `risk_scored` — Risk score computed for prioritization
  - `self_heal_retry` — Retry attempt on failed step
  - `self_heal_alternative` — Alternative strategy attempt
  - `self_heal_partial` — Partial recovery attempt
  - `learning_update` — Learning Engine data persisted
  - `priority_adjusted` — Dynamic priority re-computation
  - `concurrency_queued` — Task queued due to limit
- Logs MUST remain append-only and tamper-resistant. The
  system MUST NOT overwrite, truncate, or delete entries.

## Governance

- This Constitution supersedes all other development practices
  for the Autonomous Employee project.
- Amendments require: (1) documented rationale, (2) user
  approval, (3) version increment, and (4) a migration plan
  if principles are removed or redefined.
- Completion criteria for Gold Tier (preserved):
  - [x] All Silver Tier completion criteria remain satisfied
  - [x] Multi-step complex task execution is operational
  - [x] External API integration with permission gates works
  - [x] Conditional branching workflows execute correctly
  - [x] Real-time notifications fire on status transitions
  - [x] Automatic error recovery with rollback is verified
  - [x] `/Rollback_Archive/` folder is created and populated
  - [x] SLA thresholds are configured and breach detection works
  - [x] Operations log is append-only and tamper-evident
  - [x] Dashboard displays all Gold Tier metrics
  - [x] All 6 automation gates are enforced
  - [x] Manual review override mechanism is functional
  - [x] Alerting fires for all defined trigger conditions
- Completion criteria for Platinum Tier:
  - [ ] All Gold Tier completion criteria remain satisfied
  - [ ] Intelligent Planning Engine decomposes high-level
    requests into structured execution graphs
  - [ ] Self-Healing Execution attempts recovery before
    rollback (retry -> alternative -> partial -> fallback)
  - [ ] Predictive SLA Monitoring fires early warnings
    before breaches occur
  - [ ] Dynamic Risk-Based Prioritization adjusts execution
    order based on composite risk scores
  - [ ] Learning Engine tracks and persists execution metrics
    that influence future decisions
  - [ ] Safe Concurrency Control respects parallel limits
    and prevents deadlocks
  - [ ] Immutable Audit Log records all Platinum decisions
    with decision reason and risk scores
  - [ ] `/Learning_Data/` folder is created and populated
  - [ ] All existing 205 tests continue passing (no Gold
    regression)
  - [ ] Platinum integration tests achieve 100% coverage
    of P1-P7 capabilities
  - [ ] Environment configuration updated with Platinum
    parameters
- Versioning policy: MAJOR.MINOR.PATCH per Semantic
  Versioning. MAJOR for principle removals/redefinitions,
  MINOR for new principles/sections, PATCH for clarifications.
- Compliance review: All PRs MUST verify alignment with these
  principles. Complexity beyond what is specified here MUST be
  justified in the PR description.

**Version**: 4.0.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-11
