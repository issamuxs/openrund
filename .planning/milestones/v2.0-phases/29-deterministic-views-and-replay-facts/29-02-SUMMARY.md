---
phase: 29-deterministic-views-and-replay-facts
plan: "02"
subsystem: explanatory-view-reducers
tags: [timeline, artifacts, checkpoints, reports, immutable]
requires:
  - phase: 29-01-known-history
    provides: Validated complete known-watermark input
provides:
  - Ordered typed Timeline
  - Immutable Artifact availability index
  - Correctable Checkpoint View
  - Derived Check Reports with Artifact evidence
affects: [run-view-bundle, readiness, bundles, cli-inspection]
tech-stack:
  added: []
  patterns: [explicit Event payload dispatch, immutable ordered projection]
key-files:
  created:
    - src/openrund/views/_timeline.py
    - src/openrund/views/_artifacts.py
    - src/openrund/views/_checkpoints.py
    - src/openrund/views/_reports.py
    - tests/views/test_timeline_artifacts.py
    - tests/views/test_checkpoints_reports.py
  modified: []
key-decisions:
  - "Preserve an explicit None timeline summary rather than inventing text for Events without a defined summary."
  - "Combine Artifact facts with supplied Artifact availability without allowing Views to read a store."
  - "Keep corrected Checkpoints in history and mark them obsolete instead of rewriting or deleting them."
patterns-established:
  - "Focused reducers accept only KnownHistory and return final dataclasses, tuples, or read-only mappings."
  - "Reports retain source watermark and Check/Event identity while exposing no state-changing methods."
requirements-completed: []
coverage:
  - id: D1
    description: Timeline and Artifact index preserve order, optional summaries, metadata, previews, and availability
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_timeline_artifacts.py (4 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: Checkpoint correction and Check Reports replay immutably without authority
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_checkpoints_reports.py (3 passed)"
        status: pass
      - kind: other
        ref: "Current complete Views suite (19 passed), strict mypy and Ruff"
        status: pass
    human_judgment: false
duration: 5m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 02: Timeline, Artifacts, Checkpoints, and Reports Summary

**Four explanatory surfaces now replay in exact Event order as immutable typed facts, with no storage read or authority path.**

## Accomplishments

- Added explicit Timeline summaries with exact fallback and absence behavior.
- Added an insertion-ordered immutable Artifact index combining Event facts and supplied availability.
- Added complete/active Checkpoint projections with append-only correction semantics.
- Added watermark-bound Check Reports carrying result/evidence Artifact identities.

## Task Commits

1. **Timeline and Artifact index** — `bed2dd4`
2. **Checkpoints and Reports** — `90f9c25`

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused tests: 7 passed.
- Current Views suite: 19 passed.
- Strict mypy and Ruff: passed.
- Artifacts: 4/4; key links: 1/1.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
