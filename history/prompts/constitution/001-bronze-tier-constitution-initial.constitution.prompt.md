---
id: 001
title: Bronze Tier Constitution Initial
stage: constitution
date: 2026-02-10
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: 005-dapr-kafka-cloud-deploy
user: user
command: /sp.constitution
labels: ["constitution", "bronze-tier", "foundation", "initial-setup"]
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

Bronze Tier Constitution – Autonomous Employee Project

Project Name: autonomous_employee
Tier: Bronze (Foundation / Minimum Viable Deliverable)
Goal: Personal AI Employee ka basic version banana jo tasks ko detect kare aur vault me record kare, Claude Code se reasoning kare, aur basic AI workflow follow kare.

1. Objective

Bronze tier ka main objective ye hai ki hum ek functional foundation layer banaye jahan:

Claude Code Obsidian vault ko read/write kar sake

Ek basic Watcher (Gmail ya File System) kaam kare

Tasks ko /Needs_Action → /Done folder me track kiya ja sake

AI functionalities ko Agent Skills ke form me implement kiya ja sake
2. Vault Structure (Obsidian)

Bronze tier me vault ka structure ye hoga:

/autonomous_employee
│
├─ /Needs_Action/        # AI ke liye nayi tasks yahan aayengi
├─ /Done/                # Complete tasks move yahan hongi
├─ /Plans/               # Claude ke plans yahan store honge
├─ Dashboard.md          # Summary of recent activity
├─ Company_Handbook.md   # Rules for AI (e.g., polite responses)

3. Watchers (Perception Layer)

Minimum requirement: 1 watcher script

Option 1: Gmail Watcher → unread, important emails detect kare

Option 2: File System Watcher → new files detect kare aur /Needs_Action me store kare

Watcher ka kaam:
External input detect karna

Task ko .md file me convert karna

/Needs_Action folder me save karna

4. Claude Code (Reasoning Layer)

Role: AI ka "brain"

Task: Needs_Action folder ko read karna, plans generate karna, simple reasoning karna

Output: Plan.md file banaye jahan next steps checkboxes me hon

Ralph Wiggum loop: Claude ko continuously task complete karne ke liye chalaye

5. Action Layer

Bronze tier me action minimal:

Claude sirf Plans.md generate karega

File movement /Needs_Action → /Done manually ya orchestrator ke through
6. Implementation Rules

Claude Code ka version verify kare: claude --version

Obsidian vault create kare: autonomous_employee

Python environment setup kare (3.13+)

Watcher script run kare (e.g., python gmail_watcher.py)

Dashboard.md aur Company_Handbook.md update kare regularly

7. Security & Privacy (Minimal Bronze)

Secrets/store credentials vault me never

.env file me API keys save kare aur .gitignore me add kare

Local-only operations (Gmail/Files), koi external cloud connection optional
8. Completion Criteria

Bronze tier tab complete hoga jab:

Obsidian vault properly setup ho

Claude Code successfully read/write kar raha ho

At least 1 Watcher task detect aur Needs_Action folder me save kar raha ho

Plans folder me simple Plan.md files generate ho rahi ho

/Done folder me manually/auto task movement ka workflow functional ho

## Response snapshot

Created initial Bronze Tier Constitution v1.0.0 for the Autonomous Employee project. The constitution defines 5 core principles:
1. Functional Foundation Layer - establishes basic component communication
2. Vault-Centric Architecture - Obsidian vault structure definition
3. Perception Layer (Watchers) - task detection via Gmail/File watchers
4. Reasoning Layer (Claude Code) - AI brain for plan generation
5. Action Layer (Minimal Bronze) - intentionally minimal for foundation

Added Development Workflow, Security & Privacy, and Governance sections with completion criteria checklist.

## Outcome

- ✅ Impact: Initial constitution established for Bronze tier foundation
- 🧪 Tests: N/A (documentation artifact)
- 📁 Files: .specify/memory/constitution.md created
- 🔁 Next prompts: /sp.specify to create feature spec, vault structure setup
- 🧠 Reflection: User provided clear Bronze tier requirements; mapped 8 sections to 5 principles + 3 governance sections

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): Standard constitution template fill
- Next experiment (smallest change to try): Monitor if 5 principles are sufficient or need expansion for Silver tier
