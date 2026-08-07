---
phase: 29-deterministic-views-and-replay-facts
plan: "04"
subsystem: wait-view-reducers
tags: [waits, approvals, interactions, timers, joins, reconciliation]
requires:
  - phase: 29-01-known-history
    provides: Validated complete known-watermark input
provides:
  - Immutable queues for all five canonical Wait kinds
  - Ordered pending and terminal lifecycle evidence
  - Explicit aggregate Wait compatibility facts
affects: [run-status, engine-resume, delegation, cli-inspection]
tech-stack:
  added: []
  patterns: [typed Event variant dispatch, event-ordered immutable queues]
key-files:
  created:
    - src/openrund/views/_waits.py
    - tests/views/test_waits.py
  modified: []
key-decisions:
  - "Keep unmatched terminal Wait facts with an explicit absent request instead of fabricating pending history or discarding evidence."
  - "Retain the complete typed request and terminal payloads so kind-specific fields preserve omission and null exactly."
  - "Represent aggregate Wait creation and resumption as ordered explanatory facts outside the five identity queues."
patterns-established:
  - "Pending queues are insertion ordered; terminal Events remove only the matching kind-and-identity pair."
  - "Approval, interaction, timer, join, and reconciliation Views share one lifecycle shape without sharing authority."
requirements-completed: []
coverage:
  - id: D1
    description: All five canonical Wait kinds retain ordered pending and terminal facts
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_waits.py (5 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: Unmatched and aggregate terminal evidence remains explicit without creating authority
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_waits.py unmatched and aggregate cases"
        status: pass
      - kind: other
        ref: "Strict mypy and Ruff"
        status: pass
    human_judgment: false
duration: 10m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 04: Canonical Wait Queues Summary

**All five Wait kinds now replay into immutable pending and terminal queues while unmatched and aggregate facts remain explicit evidence.**

## Accomplishments

- Added approval, interaction, timer, join, and reconciliation queues with exact typed request and terminal payloads.
- Preserved creation order, terminal order, request identity, timestamps, decisions, outcomes, evidence, and kind-specific fields.
- Covered all twelve frozen approval/interaction/timer histories plus native join, reconciliation, unmatched, and aggregate histories.

## Task Commits

1. **Canonical Wait queue reducer and tests** — `3f31198`

## Deviations from Plan

The authenticated compatibility rows contain historical minimal Wait payloads that predate the stricter semantic constructors. Tests add only the missing test-side semantic fields before decoding; the public decoder and runtime contracts remain strict.

## Self-Check: PASSED

- Focused Wait tests: 5 passed.
- Strict mypy and Ruff: passed.
- Artifacts: 2/2; key links: 1/1.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
