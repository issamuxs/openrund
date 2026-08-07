---
phase: 30-durable-storage-artifacts-and-leases
plan: "02"
subsystem: sqlite-event-custody
tags: [python, sqlite, events, concurrency, atomicity]
requires:
  - phase: 30-01-storage-foundation
    provides: Atomic Event ports and versioned SQLite transaction kernel
provides:
  - Expected-watermark durable Event append and fail-closed ordered reads
  - One-transaction atomic multi-Run Event commits
  - Bounded writer contention and deterministic concurrency proof
affects: [engine-commit, delegation, replay, event-log]
tech-stack:
  added: []
  patterns: [pre-encode before transaction, validate-all-before-insert, normalized codec reconstruction]
key-files:
  created:
    - src/openrund/storage/_events.py
    - tests/storage/test_events.py
    - tests/storage/test_event_concurrency.py
  modified:
    - src/openrund/storage/__init__.py
    - tests/package/test_import_hygiene.py
key-decisions:
  - "Encode every Event through the public codec before opening a transaction, then persist the normalized envelope columns and compact payload JSON."
  - "Validate every Run watermark and global Event identity before inserting any row in an append-many transaction."
  - "Reconstruct codec input from normalized rows and reject any invalid, gapped, or non-contiguous history instead of returning a partial slice."
requirements-completed: [EVT-01, STO-01]
coverage:
  - id: D1
    description: Single-Run appends preserve exact watermarks, links, ordered pagination, restart behavior, and typed conflicts
    requirement: EVT-01
    verification:
      - kind: unit
        ref: "tests/storage/test_events.py (9 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over the Event adapter and tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Concurrent single- and multi-Run writes have exactly one complete winner, rollback injected faults, and bound lock waits
    requirement: EVT-01, STO-01
    verification:
      - kind: integration
        ref: "tests/storage/test_event_concurrency.py (5 passed across 5 repeated runs)"
        status: pass
    human_judgment: false
duration: 18min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 02: Durable SQLite Event Custody Summary

**Run histories now persist through exact expected-watermark commits, fail-closed reads, and atomic multi-Run transactions.**

## Accomplishments

- Added a restart-safe `SqliteRunEventStore` using the shared short-lived connection and transaction kernel.
- Preserved payload order and optional Event links through explicit public codec encoding and normalized SQLite columns.
- Added exact empty-stream, append-watermark, read-cursor, pagination, duplicate-ID, stale-position, and corruption behavior.
- Added atomic multi-Run commits that validate every stream and identity before the first insert.
- Proved one-winner concurrent writes, cross-Run non-mixing, full rollback under injected SQL faults, and finite busy outcomes.

## Task Commits

1. **Durable SQLite Event store** — `52431e8`
2. **Atomic Event concurrency proof** — `cbd08a8`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Advanced import hygiene to the Phase 30 dependency graph**

- Removed storage from the globally future-subsystem list while retaining a strict ban on contracts, ports, and Views depending on storage.
- Allowed wire envelope names only in the normalized SQLite Event boundary that reconstructs inputs for the public codec; CLI and graphical UI remain globally forbidden.

## Self-Check: PASSED

- Event adapter tests: 9 passed.
- Event concurrency tests: 5 passed across 5 repeated runs.
- Phase architecture/import hygiene: 5 passed.
- Strict mypy, Ruff, format, and `git diff --check`: passed.
- Artifacts: 3/3; key links: 2/2.

## Next Plan Readiness

Durable Event custody is ready for post-commit delivery and later Engine/Delegation transactions.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
