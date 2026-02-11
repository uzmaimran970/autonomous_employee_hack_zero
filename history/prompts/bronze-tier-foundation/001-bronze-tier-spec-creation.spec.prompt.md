---
id: 001
title: Bronze Tier Spec Creation
stage: spec
date: 2026-02-10
surface: agent
model: claude-opus-4-5-20251101
feature: bronze-tier-foundation
branch: 001-bronze-tier-foundation
user: user
command: /sp.specify
labels: ["spec", "bronze-tier", "foundation", "vault", "watchers"]
links:
  spec: /mnt/c/Users/pc/specs/001-bronze-tier-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/spec.md
  - /mnt/c/Users/pc/specs/001-bronze-tier-foundation/checklists/requirements.md
tests:
  - null
---

## Prompt

.specify/prompts/001-bronze-tier-specify.prompt.md
id: 001
title: Bronze Tier Specification
stage: specify
date: 2026-02-10
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: 005-dapr-kafka-cloud-deploy
user: user

# Purpose
Translate the Bronze Tier Constitution (v1.0.0) of the Autonomous Employee project into actionable specifications for Claude. Focus on defining tasks, watchers, and operational scope, while respecting security and privacy constraints.

# Inputs
- Constitution file: .specify/memory/constitution.md
- Core principles (5) as defined in the Constitution
- Vault folder structure: /Needs_Action, /Done, /Plans
- Development workflow notes

# Outputs
- List of actionable tasks Claude must perform
- Watcher configuration (e.g., Gmail/File watchers)
- Memory references (Vault read/write)
- Manual vs automated steps clearly separated
- Compliance with Bronze Tier limitations (minimal automation, Plans.md only)

# Guidelines
1. Use plain language instructions for Claude's internal reasoning.
2. Ensure all tasks are explicitly linked to a principle from the Constitution.
3. Mark tasks as "manual" or "automated" clearly.
4. Respect the operational scope; Bronze Tier cannot move tasks automatically in Vault.
5. Reference Plans.md for all planned actions; no extra outputs allowed.
6. Output must be structured as a Markdown checklist for easy tracking.

## Response snapshot

Created feature specification for Bronze Tier Foundation translating Constitution v1.0.0 into actionable specs:

- **Branch**: `001-bronze-tier-foundation`
- **4 User Stories**: Vault Setup (P1), Task Detection (P2), Plan Generation (P3), Task Movement (P4)
- **13 Functional Requirements**: Mapped to Constitution principles I-V plus Security
- **8 Success Criteria**: Measurable, technology-agnostic outcomes
- **4 Edge Cases**: Error handling for vault corruption, API failures, malformed files, disk space

Spec passed all quality checklist items. Ready for `/sp.clarify` or `/sp.plan`.

## Outcome

- ✅ Impact: Full Bronze tier specification created with traceability to Constitution principles
- 🧪 Tests: N/A (specification document)
- 📁 Files: spec.md, checklists/requirements.md created
- 🔁 Next prompts: /sp.clarify for requirement refinement, /sp.plan for implementation planning
- 🧠 Reflection: User input was detailed prompt file; mapped 5 principles to 13 FRs; no clarifications needed

## Evaluation notes (flywheel)

- Failure modes observed: None - input was comprehensive
- Graders run and results (PASS/FAIL): Quality checklist PASS (all items)
- Prompt variant (if applicable): Standard spec template with Constitution integration
- Next experiment (smallest change to try): Monitor if 4 user stories adequately cover all Bronze tier functionality
