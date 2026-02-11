---
id: 003
title: Gold Tier Constitution Upgrade
stage: constitution
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: gold-tier
branch: 006-silver-tier-upgrade
user: uzmaimran
command: /sp.constitution
labels: ["constitution", "gold-tier", "automation", "upgrade", "rollback", "sla"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - null
---

## Prompt

You are tasked with creating the **Gold Tier Constitution** for the Hackathon Zero "Autonomous Employee" project.
Build upon the Silver Tier principles, ensuring **all prior rules and automation gates are inherited**, and extend with advanced Gold Tier requirements.

Requirements:

1. **Baseline Principles**: Include all Silver Tier principles as the foundation, including:
   - Vault structure and safe folder operations
   - Automated task classification & execution
   - Watchers and event detection
   - Dashboard metrics and task logging
   - Credential scanning and safe operation gating

2. **Gold Tier Automation Gates**: Introduce new rules for higher complexity tasks:
   - Multi-step complex task execution
   - Safe integration with external APIs or cloud services
   - Conditional branching workflows based on task attributes
   - Real-time notifications and dashboard alerts for task status
   - Automatic error recovery with rollback capability

3. **Security & Compliance Principles**:
   - All secrets, tokens, and credentials must remain secure and never stored in the vault.
   - Pre-commit and runtime scanning for sensitive information.
   - Permission-based gating for any file, network, or API operations.
   - Operations audit log must be append-only and tamper-evident.

4. **Success Criteria**:
   - Task execution meets SLA thresholds (e.g., completion within X minutes/hours).
   - System maintains continuous operation with uptime > Y hours.
   - Unsafe or blocked operations must be detected before execution.
   - Metrics: task throughput, error rate, and rollback incidents tracked.

5. **Audit & Observability Principles**:
   - All executed tasks and movements logged in immutable JSON Lines format.
   - Dashboard metrics should track: average task completion time, error rate, in-progress count.
   - Provide optional manual review or override steps for critical tasks.
   - Alert on any deviations or failures in workflow.

6. **Implementation Notes**:
   - Do **not** include implementation details; focus only on rules, gates, and measurable criteria.
   - Use **Markdown headings and lists** for clarity.
   - Provide placeholders for **manual follow-up items** where decision or clarification may be needed.
   - Ensure the document is structured to be directly usable for **PHR creation** and as input for `/sp.specify`.

7. **Output Requirements**:
   - Sectioned clearly: Principles, Automation Gates, Security, Success Criteria, Audit & Observability.
   - Must be readable, testable, and unambiguous.
   - Highlight where new Gold Tier-specific rules extend or override Silver Tier rules.

Return only the **full markdown text** of the Constitution, ready for inclusion in Hackathon Zero Gold Tier workflow.

## Response snapshot

Upgraded the Autonomous Employee Constitution from v2.0.0 (Silver Tier) to v3.0.0 (Gold Tier). Key changes:

**Modified Principles (5 existing, all extended):**
1. **I. Functional Foundation Layer** — Added multi-step task orchestration, health-check heartbeat, graceful degradation for external service failures.
2. **II. Vault-Centric Architecture** — Added `/Rollback_Archive/` folder, task `version:` field in frontmatter, state snapshots before complex execution.
3. **III. Perception Layer (Watchers)** — Added webhook/API event sources, `priority:` field routing (critical/high/normal/low), anomalous input rate alerting.
4. **IV. Reasoning Layer (Claude Code)** — Added conditional branching workflows, dependency graph resolution, checkpoint-based multi-step plan execution.
5. **V. Action Layer** — Renamed to "Gold Orchestration"; added complex task execution with `AUTO_EXECUTE_COMPLEX`, external API permission gates (`ALLOWED_EXTERNAL_SERVICES`), automatic error recovery with rollback (snapshot → restore → mark failed_rollback), real-time notifications.

**New Sections (3 added):**
- **VI. Gold Tier Automation Gates** — 6 gates total: Step Count (extended to 15 for complex), Credential Check (inherited), Determinism Check (extended for allowlisted APIs), Permission Gate (new), SLA Feasibility Gate (new), Rollback Readiness Gate (new).
- **VII. Success Criteria & SLA** — SLA thresholds (with TODO placeholders for benchmarking), operational uptime targets, safety detection requirements, tracked metrics (throughput, error rate <5%, rollback incidents <2/day, SLA compliance >90%).
- **VIII. Audit & Observability** — Immutable operations log, expanded dashboard metrics (rollback incidents, SLA compliance), manual review & override mechanism, alerting with severity levels (critical/warning/info).

**Deferred Items (4 TODOs):** SLA_SIMPLE_MINUTES, SLA_COMPLEX_MINUTES, UPTIME_HOURS, NOTIFICATION_CHANNEL — all require user benchmarking/decision.

**Templates flagged:** plan-template.md and tasks-template.md marked as pending update to reference Gold gates and rollback tasks.

## Outcome

- ✅ Impact: Constitution upgraded from Silver v2.0.0 to Gold v3.0.0 with 3 new sections, 6 automation gates, SLA enforcement, rollback capability, and comprehensive audit/alerting framework
- 🧪 Tests: N/A (governance document, not code)
- 📁 Files: .specify/memory/constitution.md updated
- 🔁 Next prompts: /sp.specify for Gold Tier feature spec, implement rollback archive, multi-step executor, permission gates, SLA tracking
- 🧠 Reflection: MAJOR version bump justified — Gold Tier introduces backward-incompatible changes to all 5 principles and adds 3 entirely new governance sections. All Silver rules inherited as baselines, clearly labeled. 4 TODOs deferred for user benchmarking decisions.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): Standard constitution template fill with Gold Tier upgrade overlay
- Next experiment (smallest change to try): Benchmark SLA thresholds by running --loop with timing instrumentation, then fill TODO placeholders
