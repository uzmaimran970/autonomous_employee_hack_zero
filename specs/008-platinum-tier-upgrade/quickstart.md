# Quickstart: Platinum Tier Intelligence Layer

**Feature**: 008-platinum-tier-upgrade | **Date**: 2026-02-11

## Prerequisites

- Gold Tier fully operational (205 tests passing)
- Python 3.12+ with virtual environment at `.venv/`
- All Gold Tier config parameters set in `.env`

## Setup

1. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Verify Gold Tier baseline**:
   ```bash
   PYTHONPATH=src python -m pytest tests/ -q
   # Expected: 205 passed
   ```

3. **Add Platinum config to `.env`**:
   ```env
   # Platinum Tier Intelligence Layer
   PREDICTION_THRESHOLD=0.7
   MAX_PARALLEL_TASKS=3
   LEARNING_WINDOW_DAYS=30
   MAX_RECOVERY_ATTEMPTS=3
   TASK_TIMEOUT_MINUTES=15
   ENABLE_PREDICTIVE_SLA=true
   ENABLE_SELF_HEALING=true
   ENABLE_RISK_SCORING=true
   RISK_WEIGHT_SLA=0.3
   RISK_WEIGHT_COMPLEXITY=0.2
   RISK_WEIGHT_IMPACT=0.3
   RISK_WEIGHT_FAILURE=0.2
   ```

4. **Run Platinum tests** (after implementation):
   ```bash
   PYTHONPATH=src python -m pytest tests/ -q
   # Expected: 205 Gold + ~75 Platinum tests passed
   ```

## Feature Toggles

Disable any Platinum feature to revert to Gold behavior:

| Flag | Default | Effect When Disabled |
|------|---------|---------------------|
| `ENABLE_SELF_HEALING` | `true` | Skip recovery cascade; go directly to Gold rollback |
| `ENABLE_PREDICTIVE_SLA` | `true` | Skip SLA prediction loop; use Gold reactive breach detection |
| `ENABLE_RISK_SCORING` | `true` | Use Gold static priority ordering instead of risk scores |

## Architecture

```
User Request
  -> Intelligent Planning Engine (P1)
    -> Risk & Priority Engine (P4)
      -> Concurrency Controller (P6)
        -> Gold Execution Engine (Gates 1-6)
          -> Self-Healing Layer (P2)
            -> Learning Engine (P5)
              -> Immutable Audit Log (P7)
                -> Predictive SLA Monitor (P3)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/intelligence/planning_engine.py` | Task decomposition & execution graphs |
| `src/intelligence/self_healing.py` | Recovery cascade before rollback |
| `src/intelligence/sla_predictor.py` | Predictive SLA monitoring |
| `src/intelligence/risk_engine.py` | Composite risk score computation |
| `src/intelligence/learning_engine.py` | Historical metrics & optimization |
| `src/intelligence/concurrency_controller.py` | Parallel execution control |
| `src/intelligence/execution_graph.py` | ExecutionGraph data model |
