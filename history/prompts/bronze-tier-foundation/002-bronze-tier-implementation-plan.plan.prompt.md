---
id: 002
title: Bronze Tier Implementation Plan
stage: plan
date: 2026-02-10
surface: agent
model: claude-opus-4-5-20251101
feature: bronze-tier-foundation
branch: 001-bronze-tier-foundation
user: Uzma Imran
command: /sp.plan
labels: ["plan", "bronze-tier", "foundation", "implementation", "watchers", "vault"]
links:
  spec: /mnt/c/Users/pc/specs/001-bronze-tier-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/plan.md
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/research.md
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/data-model.md
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/quickstart.md
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/contracts/file-formats.md
tests:
  - null
---

## Prompt

id: 001
title: Bronze Tier Implementation Plan
stage: plan
date: 2026-02-10
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: 001-bronze-tier-foundation
user: Uzma Imran

# Context
You are tasked with creating the **Bronze Tier Implementation Plan** for the Autonomous Employee project.
The Bronze Tier specification has already been ratified, including:

- Vault setup (Obsidian folder structure)
- Task detection (Gmail/File watcher)
- Plan generation (Claude Code producing Plans.md)
- Manual/basic task movement from `/Needs_Action` → `/Done`
- Security & operational constraints (zero credentials in vault)

All functional requirements are mapped to the Bronze Tier Constitution principles.

# Goal
Produce a step-by-step **implementation plan** for Bronze Tier that is actionable and ready for execution.
Include all dependencies, order of operations, and expected outputs. Keep the plan **technology-agnostic**, but indicate if Claude code or watchers are involved.

# Requirements
1. Use **numbered checklist format** for all steps.
2. Include **expected file/folder changes** for each step.
3. Indicate **who or what agent performs each step** (Claude, Watcher, or Manual user).
4. Highlight **success criteria** for each step.
5. Add notes for **validation and verification** at the end.

# Output
Generate a plan in markdown with:

- **Implementation Steps:** Detailed, sequential, with dependencies
- **File/Folder Structure Changes:** For each step
- **Actor:** Claude / Watcher / Manual
- **Validation:** How to confirm step completion

# Constraints
- Only Bronze Tier functionality included (manual task movement, Plans.md, basic watchers)
- No Silver/Gold Tier features yet
- Security: No credentials written to vault
- Maximum clarity: Someone unfamiliar with the project should follow the plan successfully

# End
Create the **Implementation Plan markdown** ready to be saved as:
`/specs/001-bronze-tier-foundation/implementation-plan.md`

## Response snapshot

Created comprehensive Bronze Tier Implementation Plan with 5 phases:

**Phase 1: Environment & Vault Setup** (5 steps)
- Vault structure, Dashboard.md, Company_Handbook.md, Python project, environment config

**Phase 2: Watcher Implementation** (4 steps)
- Base watcher interface, File System watcher, Gmail watcher (optional), Vault manager utility

**Phase 3: Reasoning Layer** (3 steps)
- Task processor, Plan template, Continuous loop (Ralph Wiggum loop)

**Phase 4: Task Movement & Dashboard** (2 steps)
- Manual movement documentation, Dashboard updater (optional)

**Phase 5: Testing & Validation** (3 steps)
- Unit tests, Integration tests, Security audit

Generated supporting artifacts:
- research.md: 7 technical decisions with rationale
- data-model.md: 6 entities with schemas and validation rules
- quickstart.md: 10-minute setup guide
- contracts/file-formats.md: File format specifications

## Outcome

- ✅ Impact: Complete implementation plan with actionable steps and dependency graph
- 🧪 Tests: Test strategy defined (pytest with file fixtures)
- 📁 Files: plan.md, research.md, data-model.md, quickstart.md, contracts/file-formats.md
- 🔁 Next prompts: /sp.tasks to generate task list from plan
- 🧠 Reflection: Mapped all 13 FRs to implementation steps; critical path identified

## Evaluation notes (flywheel)

- Failure modes observed: None - spec was comprehensive
- Graders run and results (PASS/FAIL): Constitution check PASS (all 5 principles + security)
- Prompt variant (if applicable): Standard plan template with enhanced step format
- Next experiment (smallest change to try): Validate quickstart.md with fresh user test
