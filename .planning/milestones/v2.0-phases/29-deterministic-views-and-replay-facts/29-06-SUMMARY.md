---
phase: 29-deterministic-views-and-replay-facts
plan: "06"
subsystem: run-status-and-readiness
tags: [runs, authority, checks, artifacts, readiness]
requires:
  - phase: 29-04-waits
    provides: Ordered unresolved Wait facts
  - phase: 29-03-actions
    provides: Pending Action reconciliation facts
  - phase: 29-02-artifacts-reports
    provides: Artifact availability and Check reports
provides:
  - Terminal-safe Run lifecycle projection
  - Active Authority and policy state with complete history
  - Typed Check summaries and ordered completion-readiness blockers
affects: [engine-completion-gates, aggregate-replay, cli-readiness]
tech-stack:
  added: []
  patterns: [composed pure reducers, typed ordered blockers]
key-files:
  created:
    - src/openrund/views/_run_status.py
    - tests/views/test_run_status.py
  modified:
    - src/openrund/views/_waits.py
    - .planning/phases/29-deterministic-views-and-replay-facts/29-06-PLAN.md
key-decisions:
  - "Terminal Run Events always outrank unresolved Wait-derived waiting while the Wait evidence remains visible."
  - "Interpret only snake_case run_contract requirements already present in semantic Run metadata; wire aliases remain outside Views."
  - "Report all unresolved Action episodes but block readiness on them only when the Run contract requires known outcomes."
  - "Treat ready as immutable explanatory data with no completion, legality, or Event-append operation."
patterns-established:
  - "Readiness blocker order is pending Wait, missing required Artifact, unresolved Action, then unsatisfied semantic Check."
  - "Active Authority maps remain read-only while the full ordered grant/revoke history stays inspectable."
requirements-completed: []
coverage:
  - id: D1
    description: Run lifecycle, Authority, policy, and latest Check summaries replay with terminal precedence
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_run_status.py lifecycle, authority, and check cases"
        status: pass
    human_judgment: false
  - id: D2
    description: Readiness reports ordered Wait, Artifact, Action, and semantic Check blockers without authority
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_run_status.py (6 passed)"
        status: pass
      - kind: other
        ref: "Wave 4 Views suite (40 passed), strict mypy and Ruff"
        status: pass
    human_judgment: false
duration: 15m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 06: Run Status and Completion Readiness Summary

**Run lifecycle, active Authority, Checks, and completion readiness now compose into one immutable known-watermark explanation.**

## Accomplishments

- Added canonical unknown, created, running, waiting, and terminal Run states with terminal precedence.
- Added active capability/policy Authority maps plus ordered grant/revoke history and identity-safe revocation.
- Added named semantic and diagnostic Check summaries, source-coverage evidence, Artifact requirements, and ordered blockers.
- Kept `ready` explicitly non-authoritative and free of any mutation or completion operation.

## Task Commits

1. **Run status, Authority, Checks, and readiness** — `65d4dc0`

Both planned tasks share the same composed reducer and evidence matrix, so they were committed atomically together.

## Deviations from Plan

- Added global pending/terminal order to `WaitQueues` so cross-kind readiness blockers preserve Event order.
- Corrected the plan's Wait reducer key-link pattern from an obsolete name to `WaitQueues`.

## Self-Check: PASSED

- Focused Run-status tests: 6 passed.
- Wave 4 Views suite: 40 passed.
- Strict mypy and Ruff: passed.
- Artifacts: 2/2; key links: 2/2.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
