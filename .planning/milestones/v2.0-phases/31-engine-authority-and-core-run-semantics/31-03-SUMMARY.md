---
phase: 31-engine-authority-and-core-run-semantics
plan: "03"
subsystem: engine-authority
tags: [python, engine, events, replay, concurrency, idempotency]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Pure legality and exact durable decision evidence
  - phase: 30-durable-storage-artifacts-and-leases
    provides: Expected-position atomic Event append and complete reads
provides:
  - One public RuntimeEngine.submit mutation path
  - Atomic command.recorded plus accepted target Event batches
  - Durable duplicate recovery, explicit idempotency supersession, and bounded conflict replay
affects: [run-lifecycle, model-lifecycle, proposals, later-coordination]
tech-stack:
  added: []
  patterns: [complete replay before decide, atomic audit-first batch, optimistic conflict re-evaluation]
key-files:
  created:
    - src/openrund/engine/_engine.py
    - src/openrund/engine/_events.py
    - tests/engine/test_engine.py
    - tests/engine/test_concurrency.py
  modified:
    - src/openrund/engine/__init__.py
key-decisions:
  - "Place command.recorded first and link every accepted target Event to both its Command ID and command Event causation ID."
  - "Recover identical Command IDs exclusively from durable history and append an explicit superseded attempt for a different Command that reuses a committed idempotency key."
  - "Reallocate uncommitted Event identities after conflicts but retain the stable caller-owned Command identity across every re-evaluation."
requirements-completed: [ENG-01, ENG-02]
duration: 16min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 03: Authoritative Submit Pipeline Summary

**Every supported mutation now passes through one complete-replay Engine decision and one atomic audit-first Event append.**

## Accomplishments

- Added explicit lifecycle Event intents and exact Event envelopes for every accepted Phase 31 operation.
- Added `RuntimeEngine.submit(Command)` with complete Run reads, exact-watermark View rebuild, legality evaluation, identity allocation, and atomic expected-position append.
- Added durable duplicate Command recovery, explicit idempotency supersession, bounded retry, and full re-evaluation after optimistic conflicts.
- Enforced a public Engine surface containing only `submit`, with no append, emit, or EventStore exposure.

## Task Commits

1. **Authoritative submit pipeline** — `4e47ed4`
2. **Conflict and idempotency safety evidence** — `976d9c2`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine, View, and Event-storage focused suites: 157 passed.
- Strict mypy: passed for all Engine source and tests.
- Ruff lint/format and `git diff --check`: passed.
- Race tests prove legality changes after an intervening terminal Event and retry exhaustion remains finite.

## Next Plan Readiness

Ready for Plan 31-04 exhaustive Run lifecycle and completion readiness coverage.
