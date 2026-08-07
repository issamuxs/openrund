---
phase: 29-deterministic-views-and-replay-facts
plan: "03"
subsystem: action-view-reducers
tags: [actions, reconciliation, receipts, immutable]
requires:
  - phase: 29-01-known-history
    provides: Validated complete known-watermark input
provides:
  - Typed Action lifecycle status
  - Event-keyed pending and reconciled uncertainty facts
  - Immutable complete Action Receipts
affects: [run-view-bundle, engine-recovery, cli-inspection]
tech-stack:
  added: []
  patterns: [explicit typed Event dispatch, immutable replacement fold]
key-files:
  created:
    - src/openrund/views/_actions.py
    - tests/views/test_actions.py
  modified: []
key-decisions:
  - "Key pending uncertainty by the ActionUnknown Event identity so only an explicitly referenced episode can be reconciled."
  - "Ignore lifecycle Events for unknown Action identities instead of fabricating partial receipts."
  - "Preserve semantic timestamps, evidence, effects, mutations, errors, and Artifact references in final immutable receipt values."
patterns-established:
  - "One ordered Action fold produces status, reconciliation, and receipt surfaces without invoking a Capability."
  - "Mappings are frozen with MappingProxyType and record updates create new frozen dataclass values."
requirements-completed: []
coverage:
  - id: D1
    description: Action status covers requested, started, terminal, unknown, and reconciled histories
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_actions.py status and reconciliation cases"
        status: pass
    human_judgment: false
  - id: D2
    description: Action receipts retain complete typed lifecycle and uncertainty evidence immutably
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_actions.py (5 passed)"
        status: pass
      - kind: other
        ref: "Full suite (439 passed), strict mypy and Ruff"
        status: pass
    human_judgment: false
duration: 8m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 03: Action Status, Reconciliation, and Receipts Summary

**Action histories now reduce to immutable typed status, uncertainty, and receipt facts without executing a Capability or inventing missing Actions.**

## Accomplishments

- Added all requested, started, terminal, outcome-unknown, and reconciled Action states.
- Added pending uncertainty keyed by its source Event and append-only reconciliation outcomes.
- Added complete immutable receipts retaining timestamps, mutations, results, effects, errors, evidence, and Artifact references.

## Task Commits

1. **Action status, reconciliation, and receipts** — `5a932e1`

Both planned tasks share one ordered fold and the same source/test files, so they were committed atomically together.

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused Action tests: 5 passed.
- Full suite: 439 passed.
- Strict mypy and Ruff: passed.
- Artifacts: 2/2; key links: 1/1.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
