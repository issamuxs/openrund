---
phase: 30-durable-storage-artifacts-and-leases
plan: "03"
subsystem: post-commit-event-observation
tags: [python, events, subscribers, advisory, failure-isolation]
requires:
  - phase: 30-02-durable-event-custody
    provides: Durable expected-watermark Event store and immutable append results
provides:
  - Ordered commit-first asynchronous Event subscriber delivery
  - Sanitized subscriber failure facts and injectable reporting sink
  - Cancellation propagation without durable commit ambiguity
affects: [runtime-reporting, observability, local-assembly]
tech-stack:
  added: []
  patterns: [commit before callback, advisory failure isolation, sanitized failure fact]
key-files:
  created:
    - src/openrund/storage/_event_log.py
    - tests/storage/test_event_log.py
  modified:
    - src/openrund/storage/__init__.py
key-decisions:
  - "Deliver the exact immutable tuple returned by the durable append, in registration order, only after the store reports success."
  - "Report fixed-code failure facts containing only subscriber index and Event IDs; never retain exception messages or payloads."
  - "Catch ordinary subscriber/sink failures but propagate cancellation and process-level BaseExceptions after the durable commit."
requirements-completed: [EVT-01]
coverage:
  - id: D1
    description: Subscribers observe committed Events in order and ordinary failures cannot retry, alter, or disguise the append result
    requirement: EVT-01
    verification:
      - kind: unit
        ref: "tests/storage/test_event_log.py (5 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over the wrapper and tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Failed durable appends notify nobody, cancellation propagates, and the wrapper exposes no persistence or Authority bypass
    requirement: EVT-01
    verification:
      - kind: unit
        ref: "tests/storage/test_event_log.py plus architecture hygiene (10 passed)"
        status: pass
    human_judgment: false
duration: 8min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 03: Post-Commit Event Observation Summary

**Advisory subscribers can now observe durable Event commits without ever becoming part of commit truth, retry policy, or runtime Authority.**

## Accomplishments

- Added a narrow EventStore-compatible wrapper that delegates persistence before invoking any callback.
- Delivered the exact immutable committed tuple to ordered asynchronous subscribers.
- Isolated one or many ordinary subscriber failures and continued deterministically to later callbacks.
- Added safe fixed-shape failure reports with no exception text, payload, SQL, or path detail.
- Preserved cancellation/process termination while proving that the underlying Event remains durably committed.

## Task Commits

1. **Post-commit subscriber isolation** — `7f43fc7`

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused post-commit tests: 5 passed.
- Combined wrapper and architecture tests: 10 passed.
- Strict mypy, Ruff, format, and `git diff --check`: passed.
- AST boundary contains no SQLite, codec, Engine, append-many, legality, or Authority bypass.
- Artifacts: 2/2; key links: 1/1.

## Next Plan Readiness

All Phase 30 runtime storage behavior is implemented; compatibility and release gates remain.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
