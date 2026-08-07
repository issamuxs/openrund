---
phase: 32-governed-coordination-and-recovery
plan: "04"
subsystem: recovery
tags: [python, engine, actions, reconciliation, checks, checkpoints, annotations]
requires:
  - phase: 32-governed-coordination-and-recovery
    plan: "03"
    provides: Governed Action creation and exact Wait lifecycle
provides:
  - Atomic unknown Action and reconciliation Wait creation
  - Evidence-backed additive reconciliation with matching Wait resolution
  - Trusted semantic Checks and non-authoritative Checkpoint/Annotation facts
affects: [phase-32-delegation, phase-33-action-dispatch, phase-35-bundles]
tech-stack:
  added: []
  patterns: [explicit uncertainty, additive reconciliation, named semantic evidence]
key-files:
  created:
    - tests/engine/test_recovery.py
    - tests/engine/test_checks.py
  modified:
    - src/openrund/engine/_coordination.py
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_events.py
    - src/openrund/engine/_engine.py
key-decisions:
  - "An unknown Action and its reconciliation Wait are one accepted atomic batch; recovery never retries the effect."
  - "Only trusted-origin named semantic Check results can satisfy completion; model output, diagnostics, Checkpoints, and Annotations cannot self-authorize."
requirements-completed: [ACT-02, CHK-01]
duration: 27min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 04: Recovery and Explanatory Evidence Summary

**Consequential uncertainty is now explicit and completion-blocking until one linked, evidence-backed reconciliation resolves its exact Wait.**

## Accomplishments

- Restricted unknown marking to existing non-terminal Actions and atomically appended `action.unknown` plus a concrete reconciliation Wait.
- Required an exact current unknown Event, substantive governed evidence, and the matching pending Wait before appending additive `action.reconciled` and `wait.resolved` facts.
- Rejected blind retry, mismatched episodes, duplicate/conflicting reconciliation, empty evidence, and post-terminal contradiction.
- Added exact Check, Checkpoint, and canonical Annotation materialization with identity, count, range, protected-event, and Artifact-link validation.
- Proved that only trusted named semantic Check results affect completion readiness; diagnostics and explanatory facts remain non-authoritative.

## Task Commits

1. **Unknown outcome and reconciliation lifecycle** — `4010126`
2. **Check, Checkpoint, and Annotation evidence tests** — `19e68be`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine plus affected View suite: 90 passed.
- Strict mypy and Ruff lint/format: passed.
- Git whitespace validation: passed.

## Next Plan Readiness

Ready to establish bounded delegated Runs with atomic parent/child persistence in Plan 32-05.
