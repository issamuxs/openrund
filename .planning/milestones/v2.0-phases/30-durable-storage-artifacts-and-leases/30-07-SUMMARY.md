---
phase: 30-durable-storage-artifacts-and-leases
plan: "07"
subsystem: storage-compatibility-and-release
tags: [python, sqlite, compatibility, packaging, architecture]
requires:
  - phase: 30-01-through-30-06
    provides: Durable Event, Artifact, Lease, observer, and Run-home implementations
provides:
  - Authenticated frozen SQLite schema and persisted-row compatibility
  - Exact storage export, dependency, transaction-lifetime, and authority fences
  - Installed-wheel strict typing for every public storage adapter
  - Complete Phase 30 release-gate evidence
affects: [engine, local-assembly, packaging, compatibility-retirement]
tech-stack:
  added: []
  patterns: [authenticated evidence bijection, additive persisted-row normalization, installed-wheel typing]
key-files:
  created:
    - tests/storage/test_compatibility.py
    - tests/storage/test_hygiene.py
  modified:
    - src/openrund/storage/_events.py
    - tests/package/test_installed_typing.py
    - .planning/phases/30-durable-storage-artifacts-and-leases/30-VALIDATION.md
key-decisions:
  - "Normalize the authenticated stored run.created shape at the storage read boundary while preserving its row unchanged and keeping the canonical Event writer strict."
  - "Expose only typed custody/layout adapters from openrund.storage; keep SQLite values, connections, faults, legality, Authority, CLI, and presentation private or absent."
  - "Prove package usability against an isolated installed wheel, not the source tree."
requirements-completed: [EVT-01, ART-01, STO-01, STO-02]
coverage:
  - id: D1
    description: Every authenticated SQLite evidence row is consumed exactly once and schema/row values reopen through Python adapters without evidence mutation
    requirement: STO-01
    verification:
      - kind: compatibility
        ref: "tests/storage/test_compatibility.py (4 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: Storage exports, dependencies, errors, transaction lifetimes, blob paths, and authority boundaries are mechanically fenced
    requirement: STO-02
    verification:
      - kind: architecture
        ref: "tests/storage/test_hygiene.py (5 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: Public Event, Artifact, Lease, recovery, layout, and post-commit APIs remain strictly typed after wheel installation
    requirement: EVT-01
    verification:
      - kind: package
        ref: "tests/package/test_installed_typing.py (3 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: Complete storage implementation is tested, typed, linted, formatted, locked, and buildable
    requirement: ART-01
    verification:
      - kind: release
        ref: "625 pytest tests; strict mypy over 96 files; Ruff; uv lock; sdist and wheel"
        status: pass
    human_judgment: false
duration: 24min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 07: Storage Compatibility and Release Summary

**The complete local custody layer now preserves authenticated SQLite history, stays behind typed ports, and passes every release gate without acquiring legality, Authority, CLI, or presentation behavior.**

## Accomplishments

- Authenticated and consumed the exact 32-row SQLite evidence inventory with containment, regular-file, byte-length, SHA-256, and before/after immutability checks.
- Proved exact tables, columns, indexes, constraints, additive migration, repeated reopen, nullable Event links, and representative Event/Artifact/Lease values.
- Added a narrow storage-read normalization for the authenticated persisted `run.created` payload while proving the underlying row remains byte-for-byte unchanged.
- Sealed the public storage surface with AST dependency, connection lifetime, safe-error, relative-blob-path, no-authority, and no-presentation fences.
- Expanded installed-wheel strict typing across every public storage adapter, port, input, result, recovery value, layout helper, and post-commit wrapper.
- Passed the exact release command after review fixes: 625 tests, strict mypy over 96 files, Ruff lint/format, lock verification, sdist, and wheel.

## Task Commits

1. **Frozen SQLite compatibility** — `b8aff5e`
2. **Storage hygiene and installed typing** — `565333e`
3. **Post-plan integrity review fixes** — `182b37c`

## Deviations from Plan

- **Required correctness fix:** `src/openrund/storage/_events.py` was updated in addition to the named test files because the authenticated stored `run.created` row omits the canonical status field. The adapter now performs a narrow read-only normalization; the strict codec and frozen evidence remain unchanged.
- **Validation bookkeeping:** Updated `30-VALIDATION.md` after all Wave 0 targets and release gates became green.

## Self-Check: PASSED

- Frozen SQLite compatibility: 4 passed; evidence unchanged.
- Storage architecture and security hygiene: 5 passed.
- Installed-wheel typing and isolated import: 3 passed.
- Full suite: 625 passed.
- Strict mypy: 96 source files; Ruff lint/format: passed.
- `uv lock --check`, source distribution, wheel, and `git diff --check`: passed.
- Artifacts: 3/3; key links: 2/2.

## Next Plan Readiness

Phase 30 is implementation-complete and ready for phase goal verification and review before the Engine phase begins.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
