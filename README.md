# Autonomous Employee - Gold Tier

**Hackathon Zero Submission** | Branch: `007-gold-tier-upgrade`

An AI-powered autonomous task management system built on an Obsidian Vault. The system watches for incoming files, automatically classifies tasks through a six-gate security pipeline, executes safe operations with rollback protection, tracks SLA compliance, and sends webhook notifications — all without human intervention.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Vault Folder Structure](#vault-folder-structure)
- [Task Lifecycle](#task-lifecycle)
- [Key Modules](#key-modules)
- [Six-Gate Classification System](#six-gate-classification-system)
- [Configuration](#configuration)
- [Getting Started](#getting-started)
- [CLI Commands](#cli-commands)
- [Demo: End-to-End Task Execution](#demo-end-to-end-task-execution)
- [Test Summary](#test-summary)
- [Project Structure](#project-structure)

---

## Features

### Gold Tier Capabilities

| Feature | Description |
|---------|-------------|
| **Six-Gate Classification** | Sequential gate pipeline (step count, credentials, determinism, permissions, SLA feasibility, rollback readiness) classifying tasks as `simple`, `complex`, or `manual_review` |
| **Multi-Step Execution** | Executes all plan steps sequentially with per-step checkpoint logging and halt-on-failure |
| **Rollback Snapshots** | Pre-execution snapshots in `/Rollback_Archive/` with automatic restore on failure and configurable retention (default: 7 days) |
| **SLA Tracking** | Monitors `classified_at` to `completed_at` duration against configurable thresholds with breach detection |
| **Webhook Notifications** | Fire-and-forget HTTP POST notifications on task status changes |
| **Branch Routing** | Type-based operation routing (document, image, data, email) with priority-based queue sorting |
| **Enhanced Dashboard** | Real-time metrics: rollback incidents, SLA compliance %, throughput, active alerts |
| **Credential Scanning** | Detects API keys, tokens, passwords, PEM keys, connection strings across vault files |
| **Operations Audit Log** | JSONL audit trail of every operation with 18 operation types |
| **Health-Check Heartbeat** | Per-loop vault structure validation with `heartbeat_fail` logging |

### Inherited Silver/Bronze Capabilities

- File watcher with content-hash deduplication
- Automatic file type detection (document, image, data, email)
- Task auto-move between folders based on status
- Dashboard with activity log and statistics
- Configurable via `.env` environment variables

---

## Architecture Overview

```
                    +-----------------+
                    |   File Watcher  |   Monitors ./inbox for new files
                    +--------+--------+
                             |
                             v
                    +--------+--------+
                    |  Needs_Action/  |   Incoming tasks (pending)
                    +--------+--------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
    +---------+---------+     +-------------+-----------+
    |  Task Classifier  |     |  Credential Scanner     |
    |  (6-gate pipeline)|     |  (pattern detection)    |
    +---------+---------+     +-------------------------+
              |
    +---------+---------+
    |   Branch Router   |   Routes by type + priority
    +---------+---------+
              |
              v
    +---------+---------+
    |   In_Progress/    |   Active tasks
    +---------+---------+
              |
    +---------+---------+         +-------------------+
    |  Rollback Manager |-------->| Rollback_Archive/ |
    |  (pre-snapshot)   |         +-------------------+
    +---------+---------+
              |
              v
    +---------+---------+
    |  Task Executor    |   Multi-step, halt-on-failure
    +---------+---------+
              |
         +----+----+
         |         |
      success    failure
         |         |
         v         v
    +----+---+ +---+----------+
    |  Done/ | | Rollback     |
    +--------+ | Restore      |
               +--------------+
```

### Supporting Systems

```
+------------------+    +------------------+    +------------------+
|   SLA Tracker    |    | Webhook Notifier |    | Dashboard        |
|  breach detect   |    | fire-and-forget  |    | metrics + alerts |
+------------------+    +------------------+    +------------------+
         |                       |                       |
         +----------+------------+-----------+-----------+
                    |
              +-----+-----+
              | Operations |   JSONL audit log
              |   Logger   |   18 operation types
              +-----------+
```

---

## Vault Folder Structure

```
autonomous_employee/           # Obsidian Vault root
  Needs_Action/               # Pending tasks (status: pending)
  In_Progress/                # Active tasks being processed
  Done/                       # Completed tasks
  Plans/                      # Generated execution plans
  Rollback_Archive/           # Pre-execution snapshots (Gold Tier)
    {timestamp}-{task}/
      manifest.json           # Snapshot metadata
      task.md                 # Original task copy
      outputs/                # Associated output files
  Dashboard.md                # Live statistics and metrics
  Company_Handbook.md         # Business rules reference
  .task_hashes                # Content-hash deduplication registry
```

---

## Task Lifecycle

```
 NEW FILE          CLASSIFIED         EXECUTING          COMPLETED
 detected     +--> simple ------+--> execute steps --+--> Done/
    |         |    complex -----+    (halt-on-fail)  |
    v         |    manual_review     +               |   FAILED
 Needs_Action/|                      |               +--> Rollback
 (pending)    |                      v                    Restore
    |         |              Rollback_Archive/             |
    +--- classify ---+       (pre-snapshot)          In_Progress/
                                                     (failed/blocked)
```

### Task Status Values

| Status | Location | Description |
|--------|----------|-------------|
| `pending` | `Needs_Action/` | Awaiting classification |
| `in_progress` | `In_Progress/` | Being processed |
| `done` | `Done/` | Successfully completed |
| `failed` | `In_Progress/` | Execution failed, awaiting manual review |
| `failed_rollback` | `In_Progress/` | Restored from rollback snapshot |
| `blocked` | `In_Progress/` | Blocked by gate failure or missing snapshot |
| `manual_review` | `In_Progress/` | Requires human intervention |

### YAML Frontmatter Fields

Each task file contains YAML frontmatter with these fields:

```yaml
---
source: file_watcher
type: document
created: 2026-02-11T10:00:00
status: pending
version: 1
priority: normal
complexity: simple
gate_results:
  gate_1_step_count: pass
  gate_2_credentials: pass
  gate_3_determinism: pass
  gate_4_permissions: pass
  gate_5_sla: pass
  gate_6_rollback: skipped:simple
classified_at: 2026-02-11T10:00:05
completed_at: 2026-02-11T10:00:08
rollback_ref: 20260211-100005-task-name
---
```

---

## Key Modules

### `watchers/file_watcher.py` - FileWatcher

Monitors a directory for new files using Watchdog. On detection:
- Computes content hash for deduplication
- Detects file type (document, image, data, email)
- Creates task markdown with YAML frontmatter in `Needs_Action/`
- Tags with `version: 1` and `priority: normal`

### `processors/task_classifier.py` - TaskClassifier

Six-gate sequential classification pipeline:
- **Gate 1**: Step count (<=5 simple, <=15 complex, >15 manual_review)
- **Gate 2**: Credential keyword detection (passwords, tokens, API keys)
- **Gate 3**: Determinism check (no API calls, downloads, deployments)
- **Gate 4**: Permission check (vault-scope enforcement, service allowlist)
- **Gate 5**: SLA feasibility (estimated duration vs 150% threshold)
- **Gate 6**: Rollback readiness (Rollback_Archive exists)

Short-circuits on first failure. Supports `override: true` in frontmatter to bypass gates.

### `processors/task_executor.py` - TaskExecutor

Multi-step sequential executor with halt-on-failure:
- **Supported operations**: `file_create`, `file_copy`, `summarize`, `create_folder`, `rename_file`, `move_file`
- Per-step checkpoint logging via `step_executed` operations
- Returns structured result with `steps_executed`, `steps_total`, `step_results`

### `orchestrator/task_mover.py` - TaskMover

Automatic task movement based on frontmatter status:
- `pending` + in wrong folder -> `Needs_Action/`
- `in_progress` -> `In_Progress/`
- `done` -> `Done/`
- `failed`/`failed_rollback`/`blocked` -> stays in `In_Progress/` for review

### `orchestrator/rollback_manager.py` - RollbackManager

Pre-execution snapshot system:
- `create_snapshot()`: Copies task + outputs to `Rollback_Archive/{timestamp}-{stem}/`
- `restore_snapshot()`: Restores files on execution failure, sets status to `failed_rollback`
- `purge_expired()`: Removes snapshots older than `ROLLBACK_RETENTION_DAYS`

### `orchestrator/sla_tracker.py` - SLATracker

SLA compliance monitoring:
- Compares `classified_at` to `completed_at` against thresholds
- Logs `sla_breach` operations when thresholds are exceeded
- `compute_compliance()`: Returns compliance % over configurable time window

### `processors/branch_router.py` - BranchRouter

Type-based operation routing with priority sorting:
- `document` -> `summarize`, `image` -> `file_copy`, `data` -> `summarize`, `email` -> `summarize`
- Priority levels: `critical` (4), `high` (3), `normal` (2), `low` (1)
- Supports custom routing rule overrides

### `notifications/webhook_notifier.py` - WebhookNotifier

Fire-and-forget HTTP POST notifications:
- Sends JSON payload on task status changes
- Logs `notification_sent` / `notification_failed` to operations log
- Falls back to `NoOpNotifier` when not configured

### `security/credential_scanner.py` - CredentialScanner

Pattern-based credential detection:
- AWS access keys, API tokens, PEM private keys
- Password fields, bearer tokens, database connection strings
- Scans all vault files per loop iteration

---

## Six-Gate Classification System

```
Task Input
    |
    v
[Gate 1] Step Count -----> >15 steps? --> manual_review
    |                       >5 steps?  --> mark as complex candidate
    v
[Gate 2] Credentials -----> password/token/key found? --> complex
    |
    v
[Gate 3] Determinism -----> API/download/deploy? --> complex
    |
    v
[Gate 4] Permissions -----> outside vault scope? --> complex
    |                       unlisted service?    --> complex
    v
[Gate 5] SLA Feasibility -> est. duration > 150% SLA? --> complex
    |
    v
[Gate 6] Rollback Ready --> Rollback_Archive missing? --> complex
    |
    v
All gates passed:
    <= 5 steps --> simple (auto-execute)
    > 5 steps  --> complex (execute if AUTO_EXECUTE_COMPLEX=true)
```

Each gate result is recorded in frontmatter under `gate_results` for full auditability.

---

## Configuration

All configuration is via `.env` file. Copy `.env` to get started.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `./autonomous_employee` | Path to the Obsidian vault |
| `WATCH_DIR` | `./inbox` | Directory to monitor for new files |
| `CHECK_INTERVAL_SECONDS` | `30` | Loop interval in seconds |
| `LOG_LEVEL` | `INFO` | Logging level |

### Silver Tier Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OPERATIONS_LOG_PATH` | `./operations.log` | Path to JSONL operations log |
| `AUTO_EXECUTE_SIMPLE` | `false` | Auto-execute simple tasks |
| `CREDENTIAL_SCAN_ENABLED` | `true` | Enable credential scanning |

### Gold Tier Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_EXECUTE_COMPLEX` | `false` | Auto-execute complex tasks (requires rollback) |
| `ALLOWED_EXTERNAL_SERVICES` | *(empty)* | Comma-separated allowed service names |
| `SLA_SIMPLE_MINUTES` | `2` | SLA threshold for simple tasks |
| `SLA_COMPLEX_MINUTES` | `10` | SLA threshold for complex tasks |
| `NOTIFICATION_CHANNEL` | *(empty)* | Notification type (`webhook` or empty) |
| `NOTIFICATION_ENDPOINT` | *(empty)* | Webhook URL for notifications |
| `ROLLBACK_RETENTION_DAYS` | `7` | Days to keep rollback snapshots |

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd autonomous_employee

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize the vault
PYTHONPATH=src python -m src.main --init-vault
```

### Quick Start

```bash
# 1. Initialize vault structure
PYTHONPATH=src python -m src.main --init-vault

# 2. Check vault status
PYTHONPATH=src python -m src.main --status

# 3. Start the continuous loop
PYTHONPATH=src python -m src.main --loop --dir ./inbox
```

---

## CLI Commands

```bash
# Initialize vault with all required folders
python -m src.main --init-vault [--path /custom/path]

# Watch a directory for new files
python -m src.main --watch --dir ./inbox

# Process all pending tasks once
python -m src.main --process

# Run continuous processing loop
python -m src.main --loop [--dir ./inbox] [--interval 30]

# Show vault status and statistics
python -m src.main --status

# Import existing files as tasks
python -m src.main --import --dir ./inbox

# Scan vault for credential patterns
python -m src.main --scan

# Enable debug logging
python -m src.main --loop --debug
```

All commands require `PYTHONPATH=src` or running from the project root.

---

## Demo: End-to-End Task Execution

Follow these steps to see the full task lifecycle in action.

### Step 1: Initialize the Vault

```bash
cd autonomous_employee
source .venv/bin/activate
PYTHONPATH=src python -m src.main --init-vault
```

Expected output:
```
  Creating vault structure...
  Created: Needs_Action/
  Created: In_Progress/
  Created: Done/
  Created: Plans/
  Created: Rollback_Archive/
  Created: Dashboard.md
  Created: Company_Handbook.md
  Created: .task_hashes
  Vault initialized successfully!
```

### Step 2: Verify Vault Status

```bash
PYTHONPATH=src python -m src.main --status
```

Expected output:
```
  Vault Status: ./autonomous_employee
  ==================================================
  Structure: Valid

  Statistics:
     Pending Tasks: 0
     In-Progress Tasks: 0
     Completed Tasks: 0
     Plans Generated: 0
```

### Step 3: Create a Demo Task

Create a file that simulates an incoming task:

```bash
mkdir -p inbox
cat > inbox/meeting-notes.txt << 'EOF'
Team standup meeting notes for February 11, 2026.

Attendees: Alice, Bob, Charlie
Topics discussed:
- Sprint progress review
- Bug triage for v2.1
- Deployment schedule for next week

Action items:
- Alice: Update test coverage report
- Bob: Fix authentication timeout bug
- Charlie: Prepare demo for stakeholders
EOF
```

### Step 4: Import the File as a Task

```bash
PYTHONPATH=src python -m src.main --import --dir ./inbox
```

Expected output:
```
  Importing files from: ./inbox
  Imported 1 file(s) as tasks
```

### Step 5: Process the Task

```bash
PYTHONPATH=src python -m src.main --process
```

This will:
1. Detect the pending task in `Needs_Action/`
2. Run it through the six-gate classifier
3. Generate an execution plan in `Plans/`
4. Execute safe operations (if `AUTO_EXECUTE_SIMPLE=true`)

### Step 6: Check Final Status

```bash
PYTHONPATH=src python -m src.main --status
```

### Step 7: Run the Continuous Loop (Optional)

```bash
PYTHONPATH=src python -m src.main --loop --dir ./inbox --interval 10
```

Drop files into `./inbox/` and watch them get automatically processed. Press `Ctrl+C` to stop.

### Step 8: Scan for Credentials

```bash
PYTHONPATH=src python -m src.main --scan
```

---

## Test Summary

### Results: 200 passed, 0 failed

```
$ PYTHONPATH=src python -m pytest tests/ -v
============================= 200 passed in 55.66s =============================
```

### Test Breakdown

| Test Suite | Tests | Coverage |
|-----------|-------|----------|
| **Unit: TaskClassifier** | 16 | Silver gates (1-3) |
| **Unit: ClassifierGold** | 16 | Gold gates (4-6), manual_review, gate_results, short-circuit |
| **Unit: TaskExecutor** | 11 | Multi-step execution, halt-on-failure, all operations |
| **Unit: BranchRouter** | 12 | Type routing, priority, custom rules |
| **Unit: SLATracker** | 7 | Compliance, breach detection, estimation |
| **Unit: Notifier** | 5 | NoOp, Webhook success/failure, ops logging |
| **Unit: CredentialScanner** | 21 | All 6 patterns, vault scanning, masking |
| **Unit: DashboardUpdater** | 18 | Metrics, activity log, template rendering |
| **Unit: OperationsLogger** | 13 | JSONL logging, error counting, recent reads |
| **Unit: VaultManager** | 18 | Structure validation, file ops, movement |
| **Unit: VaultInitializer** | 7 | Folder creation, file generation |
| **Unit: HashRegistry** | 10 | Deduplication, persistence |
| **Unit: TaskMover** | 9 | Auto-move, status-based routing |
| **Integration: SilverWorkflow** | 5 | Full lifecycle, complex detection, credential scan |
| **Integration: EndToEnd** | 8 | Full workflow, deduplication, persistence, security |
| **Shared Fixtures** | - | `conftest.py` with temp vault, watch dir, sample content |

### Test Categories

- **Unit Tests** (163 tests): Isolated module testing with mocks
- **Integration Tests** (13 tests): Full workflow across multiple modules
- **Gold-Specific Tests** (40 tests): Six-gate classifier, branch router, SLA tracker, notifier, rollback

### Operations Covered by Tests

| Operation | Tested |
|-----------|--------|
| `task_created` | Integration |
| `task_classified` | Integration |
| `task_executed` | Integration |
| `task_moved` | Unit + Integration |
| `step_executed` | Unit |
| `sla_breach` | Unit |
| `rollback_triggered` | Unit |
| `rollback_restored` | Unit |
| `gate_blocked` | Unit |
| `notification_sent` | Unit |
| `notification_failed` | Unit |
| `credential_flagged` | Integration |
| `heartbeat_fail` | Source verified |

---

## Project Structure

```
autonomous_employee/
  src/
    main.py                          # CLI entry point
    processors/
      task_classifier.py             # 6-gate classification pipeline
      task_executor.py               # Multi-step execution engine
      task_processor.py              # Orchestrates classify + execute
      branch_router.py               # Type-based operation routing
    orchestrator/
      task_mover.py                  # Auto-move tasks between folders
      rollback_manager.py            # Snapshot create/restore/purge
      sla_tracker.py                 # SLA compliance monitoring
    watchers/
      base_watcher.py                # Abstract watcher + type detection
      file_watcher.py                # Directory watcher (Watchdog)
      gmail_watcher.py               # Gmail watcher (optional)
    notifications/
      notifier.py                    # Abstract Notifier + NoOpNotifier
      webhook_notifier.py            # HTTP POST webhook notifier
    security/
      credential_scanner.py          # Pattern-based secret detection
    utils/
      config.py                      # .env configuration loader
      vault_manager.py               # Vault CRUD operations
      vault_initializer.py           # Vault structure creation
      dashboard_updater.py           # Dashboard.md generation
      operations_logger.py           # JSONL audit logger
      hash_registry.py               # Content-hash deduplication
  tests/
    conftest.py                      # Shared pytest fixtures
    unit/                            # 163 unit tests
      test_classifier_gold.py        # Gold gate tests
      test_branch_router.py          # Routing tests
      test_sla_tracker.py            # SLA tests
      test_notifier.py               # Notification tests
      test_task_classifier.py        # Silver gate tests
      test_task_executor.py          # Executor tests
      test_task_mover.py             # Mover tests
      test_credential_scanner.py     # Scanner tests
      test_dashboard_updater.py      # Dashboard tests
      test_operations_logger.py      # Logger tests
      test_vault_manager.py          # Vault tests
      test_vault_initializer.py      # Initializer tests
      test_hash_registry.py          # Hash tests
    integration/                     # 13 integration tests
      test_end_to_end.py             # Full system tests
      test_silver_workflow.py        # Silver regression tests
  .env                               # Environment configuration
  requirements.txt                   # Python dependencies
  pyproject.toml                     # Project metadata
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Task Format | Markdown + YAML frontmatter |
| File Watching | Watchdog |
| Configuration | python-dotenv |
| Frontmatter | python-frontmatter |
| Testing | pytest |
| Notifications | urllib (stdlib) |
| Logging | Python logging + JSONL |

---

## License

Hackathon Zero submission. All rights reserved.

---

*Built with Spec-Driven Development (SDD) methodology. 200 tests. Zero failures.*
