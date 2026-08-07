---
phase: 30-durable-storage-artifacts-and-leases
plan: "01"
subsystem: durable-storage-foundation
tags: [python, sqlite, events, artifacts, leases]
requires:
  - phase: 28-python-contract-kernel
    provides: Typed Events, Artifacts, IDs, safe errors, paths, and dependency ports
  - phase: 29-deterministic-views-and-replay-facts
    provides: Exact known-watermark and replay cursor semantics
provides:
  - Precise atomic Event, immutable Artifact custody, and token-fenced Lease contracts
  - Versioned additive SQLite schema and safe transaction kernel
  - Deterministic in-memory reference behavior for corrected storage ports
affects: [phase-30-adapters, engine-commit, local-run-custody]
tech-stack:
  added: []
  patterns: [short-lived SQLite connections, explicit BEGIN IMMEDIATE, additive user_version migrations, fenced coordination token]
key-files:
  created:
    - src/openrund/storage/__init__.py
    - src/openrund/storage/_database.py
    - tests/storage/conftest.py
    - tests/storage/test_database.py
  modified:
    - src/openrund/contracts/runs.py
    - src/openrund/errors.py
    - src/openrund/ports/events.py
    - src/openrund/ports/artifacts.py
    - src/openrund/ports/leases.py
    - src/openrund/_testing/memory.py
    - tests/contracts/test_concepts.py
    - tests/ports/test_store_protocols.py
    - tests/ports/test_memory_stores.py
key-decisions:
  - "Keep append watermarks distinct from read cursors: the empty stream watermark is zero, persisted Events start at one, and a non-empty page cursor is last position plus one."
  - "Use one short-lived SQLite connection per operation with WAL, foreign keys, FULL synchronous durability, a finite busy timeout, and explicit BEGIN IMMEDIATE writes."
  - "Evolve the authenticated schema only through additive user_version migrations while rejecting newer or structurally invalid databases."
requirements-completed: [EVT-01, ART-01, STO-01, STO-02]
coverage:
  - id: D1
    description: Durable storage ports encode atomic Event batches, immutable Artifact custody, exact cursors, and token-fenced Lease mutations
    requirement: EVT-01, ART-01, STO-02
    verification:
      - kind: unit
        ref: "tests/ports/test_store_protocols.py and tests/ports/test_memory_stores.py (11 passed)"
        status: pass
      - kind: other
        ref: "strict mypy over ports, memory stores, and focused tests"
        status: pass
    human_judgment: false
  - id: D2
    description: SQLite setup is additive, idempotent, durable, finitely bounded under contention, and fail-closed on invalid schemas
    requirement: STO-01
    verification:
      - kind: unit
        ref: "tests/storage/test_database.py (9 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over the SQLite kernel and tests"
        status: pass
    human_judgment: false
duration: 12min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 01: Durable Storage Contracts and SQLite Kernel Summary

**Every durable adapter now shares precise Python storage contracts and one safe, versioned SQLite transaction boundary.**

## Accomplishments

- Corrected Event append/read position semantics, added atomic multi-Run appends, and made the deterministic memory store enforce all-or-nothing commits.
- Separated replay Artifacts from immutable custody entries with validated content length, SHA-256, unavailable state, and copied metadata.
- Fenced Lease renewal and release with opaque tokens, including stale-token and expiry behavior in the reference store.
- Added additive SQLite migrations for the authenticated Event, Artifact, and Lease schema with exact indexes and constraints.
- Added short-lived configured connections, explicit write transactions and rollback, finite lock outcomes, safe error translation, and reopen stability.

## Task Commits

1. **Durable storage contracts** — `a10d2ab`
2. **Versioned SQLite kernel** — `d945995`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Coverage] Extended concept construction tests for fenced Leases**

- Updated `tests/contracts/test_concepts.py` because adding the mandatory token intentionally changed the Lease constructor used by the existing semantic contract suite.

## Self-Check: PASSED

- Focused port tests: 11 passed.
- SQLite kernel tests: 9 passed.
- Strict mypy: passed for every touched contract, adapter, and focused test.
- Ruff and `git diff --check`: passed.
- Artifacts: 4/4; key links: 2/2.

## Next Plan Readiness

Ready for plan 30-06 and the remaining durable SQLite adapters.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
