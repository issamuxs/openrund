---
phase: 32-governed-coordination-and-recovery
plan: "02"
subsystem: waits
tags: [python, engine, waits, timers, joins, approval]
requires:
  - phase: 32-governed-coordination-and-recovery
    plan: "01"
    provides: Typed coordination operations and Wait identity factory
provides:
  - Engine-authoritative Wait request and terminal transitions
  - Exact-kind pending lookup with timer/deadline and join readiness checks
  - Replay-proven waiting state and exact-once terminal behavior
affects: [phase-32-approval, phase-32-recovery, phase-32-delegation]
tech-stack:
  added: []
  patterns: [exact-kind pending lookup, injected clock boundary, explicit join resolution]
key-files:
  created:
    - src/openrund/engine/_coordination.py
    - tests/engine/test_wait_lifecycle.py
  modified:
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_events.py
    - src/openrund/engine/_engine.py
key-decisions:
  - "Keep aggregate waiting evidence explanatory; concrete Wait requests own exact-once legality."
  - "A satisfied join remains pending until a separate resolve Command commits its terminal Event."
requirements-completed: [WAIT-01]
duration: 20min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 02: Wait Lifecycle Summary

**Approval, interaction, timer, join, and reconciliation Waits now share one exact-kind, exact-once Engine lifecycle.**

## Accomplishments

- Added pure pending lookup, duplicate detection, deadline/timer checks, join readiness, and exact payload construction.
- Materialized accepted Wait requests and resolved/cancelled/expired terminal variants through the existing ordered Command append.
- Proved waiting View derivation, early timer rejection, five-kind cancellation, duplicate terminal rejection, and explicit join resolution.
- Updated provider proposal evidence so newly supported interaction Wait proposals remain Engine-evaluated rather than gaining provider authority.

## Task Commits

1. **Authoritative Wait lifecycle** — `739073a`
2. **Exact-once Wait transition evidence** — `a39e5bc`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine suite: 67 passed.
- Wait and Run-status Views: 20 focused tests passed.
- Strict mypy and Ruff: passed.

## Next Plan Readiness

Ready to add governed Action evaluation and two-Command approval revalidation in Plan 32-03.
