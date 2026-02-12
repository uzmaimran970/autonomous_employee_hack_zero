# Research: Platinum Tier Intelligence Layer

**Feature**: 008-platinum-tier-upgrade | **Date**: 2026-02-11 | **Phase**: 0

## Purpose

Resolve all technical unknowns and research decisions needed before implementation begins.

---

## R1: Heuristic Task Decomposition Strategy

**Decision**: Keyword-based step decomposition with type-based templates

**Rationale**: The spec mandates heuristic-only intelligence (no ML/LLM). Keyword matching against task content combined with predefined step templates per task type (e.g., "document" tasks → read → analyze → generate → review) provides deterministic, testable behavior without external dependencies.

**Alternatives considered**:
- Rule engine (Drools-style): Too heavyweight for hackathon scope; requires rule definition language
- LLM-based decomposition: Explicitly excluded by spec constraints (no external API calls)
- Regex pattern matching: Too fragile; keyword sets with fuzzy matching provide better coverage

---

## R2: Statistical SLA Prediction Method

**Decision**: Normal distribution approximation using historical mean and variance

**Rationale**: For predicting P(duration > threshold), a normal distribution approximation from historical task durations is simple, statistically sound for moderate sample sizes, and requires no external libraries. The breach probability is computed as: `P = 1 - Φ((threshold - elapsed) / σ)` where Φ is the cumulative distribution function.

**Alternatives considered**:
- Exponential distribution: Better for inter-arrival times but poor fit for task durations
- Empirical CDF: More accurate but requires larger sample sizes and sorting overhead
- Machine learning regression: Excluded by spec (no ML dependencies)

**Implementation note**: Python's `statistics` module provides `mean()` and `stdev()`. The CDF can be approximated using `math.erf()` (standard library, no external deps).

---

## R3: Concurrency Model

**Decision**: Threading with `threading.Semaphore` for task limiting

**Rationale**: The spec states "single Python process" concurrency. Python's `threading.Semaphore` provides the simplest concurrency primitive for limiting parallel task count. While the GIL limits true parallelism for CPU-bound work, our tasks are I/O-bound (file system operations), so threading provides genuine concurrency. `asyncio` was considered but would require rewriting the existing synchronous Gold execution flow.

**Alternatives considered**:
- `asyncio`: Would require major refactoring of Gold synchronous code; breaks backward compatibility
- `multiprocessing`: Overkill for file-system I/O tasks; process overhead not justified
- `concurrent.futures.ThreadPoolExecutor`: Viable, but Semaphore gives more granular control

---

## R4: Learning Data Storage Format

**Decision**: JSON Lines (.jsonl) files in `/Learning_Data/`, one file per task type

**Rationale**: JSON Lines is consistent with the existing `operations.log` format (JSON Lines). One file per task type keeps data partitioned for efficient queries. The existing `json` standard library handles serialization. No external database needed.

**Alternatives considered**:
- SQLite: More powerful queries but adds a dependency and deviates from vault-centric file approach
- Single JSON file: Risk of data loss on concurrent writes; harder to purge individual records
- CSV: Less flexible for nested data; JSON is already used throughout the project

---

## R5: Execution Graph Data Structure

**Decision**: Adjacency list representation with step objects

**Rationale**: An adjacency list (dict of step_id -> [dependent_step_ids]) is simple to serialize to JSON, easy to traverse for dependency resolution, and supports topological sorting for execution ordering. Step objects carry metadata (name, priority, alternative_step, estimated_duration).

**Alternatives considered**:
- Adjacency matrix: Memory-inefficient for sparse graphs typical of task plans
- Edge list: Harder to query "what are step X's dependencies?"
- NetworkX graph: External dependency; overkill for small task graphs (3-15 steps)

---

## R6: Self-Healing Recovery Strategy Selection

**Decision**: Fixed cascade order: retry → alternative → partial → Gold fallback

**Rationale**: The constitution (Section IX, P2) defines this exact cascade order. A fixed order simplifies implementation and testing. Each strategy is attempted once before moving to the next. The cascade terminates on first success or after all strategies exhaust.

**Alternatives considered**:
- Adaptive strategy selection based on error type: More intelligent but spec defines fixed cascade
- Parallel recovery attempts: Risk of resource conflicts; fixed order is safer
- User-configurable cascade order: Over-engineering for hackathon scope

---

## R7: Risk Score Component Normalization

**Decision**: Normalize all 4 components to 0.0-1.0 range before applying weights

**Rationale**: The composite formula uses weighted sum. For the sum to be meaningful, all components must be on the same scale. Normalization: sla_risk=probability (already 0-1), complexity=simple(0.33)/complex(0.67)/manual(1.0), impact=low(0.25)/normal(0.5)/high(0.75)/critical(1.0), failure_rate=percentage (already 0-1).

**Alternatives considered**:
- Raw values without normalization: Weights become meaningless when scales differ
- Min-max normalization from historical data: Requires sufficient history; cold start problem
- Z-score normalization: Overkill; predetermined ranges work for our known component types

---

## R8: Feature Flag Implementation Pattern

**Decision**: Config-level boolean flags checked at module entry points

**Rationale**: Each Platinum feature checks its `ENABLE_*` flag at the entry point of its integration with existing code. When disabled, the code path skips the Platinum module entirely and falls through to Gold behavior. This keeps the Gold code path unchanged and testable independently.

**Alternatives considered**:
- Strategy pattern with interchangeable implementations: Over-engineered for on/off toggles
- Decorator-based feature flags: More elegant but harder to test and debug
- Runtime feature flag service: External dependency; not justified for local execution

---

## Summary

| Research Item | Decision | External Deps | Risk |
|--------------|----------|---------------|------|
| R1: Task Decomposition | Keyword + templates | None | Low — deterministic, testable |
| R2: SLA Prediction | Normal distribution (math.erf) | None | Low — standard library only |
| R3: Concurrency | threading.Semaphore | None | Medium — GIL limits, but tasks are I/O-bound |
| R4: Learning Storage | JSON Lines per task type | None | Low — consistent with ops log |
| R5: Execution Graph | Adjacency list + step objects | None | Low — simple, serializable |
| R6: Self-Healing | Fixed cascade per constitution | None | Low — spec-defined order |
| R7: Risk Normalization | 0-1 range for all components | None | Low — predetermined scales |
| R8: Feature Flags | Config booleans at entry points | None | Low — simple on/off toggle |

**All NEEDS CLARIFICATION items resolved.** No external dependencies introduced. All decisions use Python standard library only.
