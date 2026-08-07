---
phase: 31-engine-authority-and-core-run-semantics
plan: "02"
subsystem: engine-legality
tags: [python, engine, legality, decisions, replay]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Typed Phase 31 operations and canonical Content commitments
provides:
  - Pure core lifecycle and entity legality evaluation from complete replay facts
  - Exact accepted, rejected, deferred, and superseded durable decision records
  - Writer support for legitimate explicit supersession evidence
affects: [engine-submit, run-lifecycle, model-lifecycle, command-audit]
tech-stack:
  added: []
  patterns: [pure legality function, terminal-first invariants, explicit decision branch mapping]
key-files:
  created:
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_records.py
    - tests/engine/test_legality.py
  modified:
    - src/openrund/codec/_decisions.py
    - tests/engine/test_records.py
key-decisions:
  - "Evaluate Message and ModelCall entity state by deterministic Event-history reduction alongside the complete Run View bundle because Phase 29 intentionally has no authoritative entity-state View."
  - "Reject terminal Run mutations before operation-specific evaluation and translate each completion blocker into its own criterion trace entry."
  - "Permit superseded records only as explicit declaration-only evidence with an absent target and replacement Command link."
requirements-completed: []
duration: 14min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 02: Pure Legality and Durable Decision Evidence Summary

**Core Run, Message, and ModelCall legality is now deterministic, terminal-safe, and losslessly representable as durable command evidence.**

## Accomplishments

- Added a side-effect-free evaluator for no-Run, created, active, waiting, and terminal lifecycle states.
- Added Message and ModelCall entity transition checks derived from immutable Event history.
- Added exhaustive completion-blocker trace mapping for Waits, Artifacts, Checks, and unknown outcomes.
- Added exact durable record/payload construction for accepted, rejected, deferred, and superseded Commands with canonical Content hashes and full origin metadata.

## Task Commits

1. **Core Engine legality** — `75e7a1b`
2. **Durable command decision evidence** — `cccf8c1`

## Deviations from Plan

### Auto-fixed Issues

- Added `src/openrund/codec/_decisions.py` to the plan because Phase 31 introduces the first legitimate declaration-only supersession path; the frozen writer guard had correctly prohibited it before that path existed.

## Self-Check: PASSED

- Focused and affected suites: 29 passed.
- Strict mypy: passed for all Engine and plan tests.
- Ruff lint/format and `git diff --check`: passed.
- All four decision branches and every core lifecycle state have direct assertions.

## Next Plan Readiness

Ready for Plan 31-03 single-path replay/evaluate/atomic-append orchestration.
