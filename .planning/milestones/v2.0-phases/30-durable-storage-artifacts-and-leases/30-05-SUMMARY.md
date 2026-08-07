---
phase: 30-durable-storage-artifacts-and-leases
plan: "05"
subsystem: sqlite-lease-coordination
tags: [python, sqlite, leases, fencing, concurrency]
requires:
  - phase: 30-01-storage-foundation
    provides: Token-fenced Lease contracts and immediate SQLite transactions
provides:
  - Strictly expiring one-per-Run execution Leases
  - Token-fenced renew, replacement, and release behavior
  - Deterministic injectable identity/token generation and concurrent acquisition proof
affects: [engine-executors, recovery, worker-coordination]
tech-stack:
  added: []
  patterns: [caller-supplied time, opaque fencing token, conditional immediate transaction]
key-files:
  created:
    - src/openrund/storage/_leases.py
    - tests/storage/test_leases.py
  modified:
    - src/openrund/storage/__init__.py
key-decisions:
  - "Require injected synchronous Lease-ID and token factories so storage owns no hidden entropy or wall-clock source."
  - "Treat expires_at greater than supplied now as the only active boundary; exact equality is expired."
  - "Retain an expired row until replacement so reacquisition can reject a repeated fencing token before atomically replacing custody."
requirements-completed: [STO-02]
coverage:
  - id: D1
    description: Acquire, renew, release, expiry, reopen, stale identity/owner/token/Run fences, and replacement semantics are exact
    requirement: STO-02
    verification:
      - kind: unit
        ref: "tests/storage/test_leases.py (10 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over Lease storage and tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Independent adapters produce exactly one active winner and finite busy outcomes without internal time reads
    requirement: STO-02
    verification:
      - kind: integration
        ref: "tests/storage/test_leases.py repeated 5 times (50 passed)"
        status: pass
      - kind: other
        ref: "Phase architecture/import hygiene (5 passed)"
        status: pass
    human_judgment: false
duration: 13min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 05: Token-Fenced SQLite Leases Summary

**Executors now have process-safe, strictly expiring local coordination whose opaque fencing tokens convey no runtime Authority.**

## Accomplishments

- Added immediate-transaction acquire with a unique one-per-Run race guard and exact active/expired boundary.
- Added exact ID, Run, owner, and token fencing for renewal, extended only from caller-supplied time.
- Added token-fenced release and replacement behavior that defeats stale holders after reacquisition.
- Added injected validated Lease-ID/token sources, duplicate-output rollback, restart persistence, and no hidden wall-clock access.
- Proved one winner across independent adapters and a finite typed outcome under an externally held writer lock.

## Task Commits

1. **Token-fenced SQLite Lease coordination** — `95bdc98`

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused Lease tests: 10 passed.
- Concurrency suite repeated five times: 50 passed.
- Architecture/import hygiene: 5 passed.
- Strict mypy, Ruff, format, and `git diff --check`: passed.
- Artifacts: 2/2; key links: 2/2.

## Next Plan Readiness

Wave 2 storage adapters are complete and ready for post-commit Event delivery plus compatibility/release gates.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
