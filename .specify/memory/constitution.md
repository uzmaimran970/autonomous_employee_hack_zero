<!--
  ============================================================
  SYNC IMPACT REPORT
  ============================================================
  Version change: 2.0.0 → 3.0.0 (MAJOR)
  Bump rationale: Gold Tier introduces backward-incompatible
    upgrades to all 5 principles and adds 3 new top-level
    sections (Automation Gates, Success Criteria, Audit &
    Observability). Multi-step complex execution, external
    API gating, conditional workflows, rollback capability,
    and SLA enforcement constitute fundamental governance
    changes.

  Modified principles:
    - I. Functional Foundation Layer: added multi-step task
      orchestration, health-check heartbeat, graceful
      degradation for external service failures
    - II. Vault-Centric Architecture: added /Rollback_Archive
      folder, task versioning, state snapshots before
      execution
    - III. Perception Layer (Watchers): added webhook and
      API event sources, priority-based routing, alert
      triggers on anomalous input rates
    - IV. Reasoning Layer (Claude Code): added conditional
      branching, dependency graph resolution, multi-step
      plan orchestration with checkpoints
    - V. Action Layer: renamed from "Silver Automation" to
      "Gold Orchestration"; added complex task execution,
      external API integration with permission gates,
      automatic error recovery with rollback

  Added sections:
    - VI. Gold Tier Automation Gates (new)
    - VII. Success Criteria & SLA (new)
    - VIII. Audit & Observability (new)

  Removed sections: None

  Templates requiring updates:
    - .specify/templates/plan-template.md ⚠ pending
      (Constitution Check should reference Gold gates)
    - .specify/templates/spec-template.md ✅ No update needed
      (generic user story format remains compatible)
    - .specify/templates/tasks-template.md ⚠ pending
      (phase structure should account for rollback tasks)
    - .specify/templates/commands/ ✅ No command files exist

  Deferred items:
    - TODO(SLA_SIMPLE_MINUTES): Exact SLA threshold for
      simple tasks requires benchmarking
    - TODO(SLA_COMPLEX_MINUTES): Exact SLA threshold for
      complex tasks requires benchmarking
    - TODO(UPTIME_HOURS): Continuous operation target
      requires production observation
    - TODO(NOTIFICATION_CHANNEL): Real-time notification
      delivery mechanism (Slack, webhook, email) requires
      user decision
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

### II. Vault-Centric Architecture

- Obsidian Vault is the single source of truth for all task
  state. The canonical folder structure is:
  - `/Needs_Action/` — New tasks awaiting processing
  - `/In_Progress/` — Tasks currently being executed
  - `/Done/` — Completed tasks
  - `/Plans/` — Claude-generated plans and reasoning artifacts
  - `/Rollback_Archive/` — Pre-execution state snapshots
    for rollback capability **(Gold Tier)**
- `Dashboard.md` MUST reflect current task counts, SLA
  compliance, and recent activity. `Company_Handbook.md`
  defines behavioral rules.
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

### III. Perception Layer (Watchers)

- At least one Watcher script MUST be operational at all times
  during active use (Gmail Watcher, File System Watcher, or
  API Webhook Watcher).
- Watchers MUST convert detected input into `.md` task files
  and save them to `/Needs_Action/`.
- Silver Baseline: Watchers MUST support real-time recognition
  of incoming tasks (polling interval ≤ 30 seconds or
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

### IV. Reasoning Layer (Claude Code)

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

### V. Action Layer (Gold Orchestration)

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
  task status transitions (pending → in_progress → done/failed)
  via a configurable notification channel.
  TODO(NOTIFICATION_CHANNEL): Delivery mechanism (Slack,
  webhook, email) requires user decision.

## VI. Gold Tier Automation Gates

*These gates extend the Silver Tier three-gate classification
system. A task MUST pass ALL applicable gates before
auto-execution.*

### Gate 1: Step Count (inherited, extended)

- Simple tasks: ≤ 5 actionable steps (Silver baseline).
- Complex tasks: ≤ 15 actionable steps with checkpoint
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

### Gate 4: Permission Gate (Gold Tier — new)

- File operations: ALLOWED by default within the Vault.
- Network/API operations: ALLOWED only if the target service
  is listed in `ALLOWED_EXTERNAL_SERVICES` in `.env`.
- Destructive operations (file deletion, overwrite of
  existing content): MUST require explicit `destructive: true`
  flag in the task frontmatter and MUST snapshot to
  `/Rollback_Archive/` before execution.
- Operations outside the Vault directory tree MUST be blocked.

### Gate 5: SLA Feasibility Gate (Gold Tier — new)

- Before execution, the system MUST estimate whether the task
  can complete within the applicable SLA threshold.
- If estimated duration exceeds the SLA by more than 50%, the
  task MUST be flagged for manual review.
- Estimation MAY use historical average completion times from
  the operations log.

### Gate 6: Rollback Readiness Gate (Gold Tier — new)

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

- Simple task completion: MUST complete within
  TODO(SLA_SIMPLE_MINUTES) minutes from classification to
  `status: done`.
- Complex task completion: MUST complete within
  TODO(SLA_COMPLEX_MINUTES) minutes from classification to
  `status: done`.
- SLA breaches MUST be logged as `sla_breach` events in the
  operations log and surfaced on the dashboard.

### Operational Uptime

- The system MUST maintain continuous operation for at least
  TODO(UPTIME_HOURS) hours without manual restart when
  running in `--loop` mode.
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
- Alert severity levels: `critical`, `warning`, `info`.
- Critical alerts MUST be surfaced immediately; warning and
  info alerts MUST appear on the next dashboard refresh.

## Governance

- This Constitution supersedes all other development practices
  for the Autonomous Employee project.
- Amendments require: (1) documented rationale, (2) user
  approval, (3) version increment, and (4) a migration plan
  if principles are removed or redefined.
- Completion criteria for Gold Tier:
  - [ ] All Silver Tier completion criteria remain satisfied
  - [ ] Multi-step complex task execution is operational
  - [ ] External API integration with permission gates works
  - [ ] Conditional branching workflows execute correctly
  - [ ] Real-time notifications fire on status transitions
  - [ ] Automatic error recovery with rollback is verified
  - [ ] `/Rollback_Archive/` folder is created and populated
  - [ ] SLA thresholds are configured and breach detection works
  - [ ] Operations log is append-only and tamper-evident
  - [ ] Dashboard displays all Gold Tier metrics
  - [ ] All 6 automation gates are enforced
  - [ ] Manual review override mechanism is functional
  - [ ] Alerting fires for all defined trigger conditions
- Versioning policy: MAJOR.MINOR.PATCH per Semantic
  Versioning. MAJOR for principle removals/redefinitions,
  MINOR for new principles/sections, PATCH for clarifications.
- Compliance review: All PRs MUST verify alignment with these
  principles. Complexity beyond what is specified here MUST be
  justified in the PR description.

**Version**: 3.0.0 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-11
