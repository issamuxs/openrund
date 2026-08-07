---
phase: 30-durable-storage-artifacts-and-leases
plan: "06"
subsystem: run-home-layout
tags: [python, paths, custody, containment, symlinks]
requires:
  - phase: 28-python-contract-kernel
    provides: Typed Run IDs and lexical local path normalization
provides:
  - Pure deterministic Run-home layout values
  - Explicit symlink-aware contained directory materialization
  - Separate default host convention with configurable roots
affects: [artifact-custody, engine-assembly, bundles, governed-workspaces]
tech-stack:
  added: []
  patterns: [pure path construction, explicit materialization, component-by-component lstat]
key-files:
  created:
    - src/openrund/storage/_layout.py
    - tests/storage/test_layout.py
  modified:
    - src/openrund/storage/__init__.py
key-decisions:
  - "Keep the configurable root mandatory in run_home and expose the ~/.openrund host convention through a separate pure helper."
  - "Treat Run IDs as typed but still untrusted filesystem components, rejecting both separator conventions, dot components, NUL, and Windows drive spellings."
  - "Make directory creation explicit and reject symlink or non-directory components before verifying resolved containment."
requirements-completed: [STO-02]
coverage:
  - id: D1
    description: The same explicit root and Run ID produce exact runtime, workspace, and exports paths without filesystem writes
    requirement: STO-02
    verification:
      - kind: unit
        ref: "tests/storage/test_layout.py#test_run_home_is_pure_deterministic_and_configurable"
        status: pass
    human_judgment: false
  - id: D2
    description: Materialization is idempotent, contained, and refuses unsafe IDs, symlinks, and non-directories
    requirement: STO-02
    verification:
      - kind: unit
        ref: "tests/storage/test_layout.py (14 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over the layout and tests"
        status: pass
    human_judgment: false
duration: 5min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 06: Deterministic Run-Home Layout Summary

**Each Run now has stable configurable custody paths with explicit safe materialization and no implied Authority.**

## Accomplishments

- Added frozen `RunHome` values and a pure constructor for exact `runtime/`, `workspace/`, and `exports/` paths.
- Added a separate default OpenRund home convention so callers can override custody roots without hidden global configuration.
- Revalidated typed Run IDs as one platform-safe component across POSIX and Windows spellings.
- Added component-by-component creation that refuses symlinks and non-directories and verifies resolved root containment.

## Task Commits

1. **Deterministic Run-home layout** — `ee23682`

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused layout tests: 14 passed.
- Strict mypy: passed.
- Ruff and `git diff --check`: passed.
- Artifacts: 2/2; key links: 1/1.

## Next Plan Readiness

Wave 1 is complete; the SQLite kernel and Run-home paths are ready for Event, Artifact, and Lease adapters.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
