---
phase: 31-engine-authority-and-core-run-semantics
plan: "04"
subsystem: run-lifecycle
tags: [python, engine, runs, completion, terminal-state]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Authoritative submit pipeline and replay-derived legality
provides:
  - Exact root and child Run bootstrap descriptors
  - Lawful start, fail, cancel, and permanent terminal transitions
  - Exhaustive Engine-enforced completion blocker evidence
affects: [coordination, delegation, provider-loop, cli]
tech-stack:
  added: []
  patterns: [command-first bootstrap, permanent terminal state, blocker-per-trace-entry]
key-files:
  created:
    - tests/engine/test_run_lifecycle.py
    - tests/engine/test_completion.py
  modified:
    - src/openrund/engine/_legality.py
key-decisions:
  - "A root bootstrap requires root_id == run_id, while a child bootstrap requires a distinct parent and may preserve an ancestor root ID."
  - "Completion denial is one rejected Command with a separate deterministic trace entry for every current blocker."
requirements-completed: [RUN-01]
duration: 8min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 04: Run Lifecycle and Completion Summary

**Run bootstrap and terminal transitions are now proven permanent, auditable, and exhaustive with respect to completion requirements.**

## Accomplishments

- Proved command-first atomic bootstrap for roots and child descriptors, including exact title/objective/metadata/start reason.
- Proved created-to-running, fail, cancel, and post-terminal rejection behavior through the same submit path.
- Proved every pending Wait, missing Artifact kind, unknown Action outcome, and unsatisfied semantic Check appears in completion rejection evidence.
- Proved completion succeeds only when every replay-derived requirement is present.

## Task Commits

1. **Authoritative Run lifecycle** — `c281575`
2. **Exhaustive completion blockers** — `07b4d8c`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine and Run-View suites: 36 passed.
- Strict mypy: passed for all Engine source and tests.
- Ruff and `git diff --check`: passed.

## Next Plan Readiness

Ready for Plan 31-05 Message and ModelCall lifecycle semantics.
