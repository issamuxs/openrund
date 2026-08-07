---
phase: 30-durable-storage-artifacts-and-leases
plan: "04"
subsystem: artifact-custody-recovery
tags: [python, sqlite, filesystem, sha256, crash-recovery]
requires:
  - phase: 30-01-storage-foundation
    provides: Immutable ArtifactEntry port and versioned SQLite metadata table
provides:
  - Immutable SQLite Artifact metadata and absent-only local blob publication
  - Length/SHA-256 verification on write, reopen, and read
  - Explicit idempotent recovery for every filesystem/metadata crash window
affects: [engine-artifacts, checks, bundles, document-capability]
tech-stack:
  added: []
  patterns: [exclusive stage and fsync, absent-only hard-link publish, deterministic orphan quarantine]
key-files:
  created:
    - src/openrund/storage/_artifacts.py
    - tests/storage/test_artifacts.py
    - tests/storage/test_artifact_recovery.py
  modified:
    - src/openrund/storage/__init__.py
key-decisions:
  - "Publish blob bytes through an exclusive synced stage and absent-only hard link before committing immutable relative-path metadata."
  - "Require callers to supply the recovery observation timestamp so storage never invents wall-clock facts when marking content unavailable."
  - "Scan only recognized regular entries in runtime-owned staging and blob directories; leave unrelated and symlinked entries untouched."
requirements-completed: [ART-01, STO-01]
coverage:
  - id: D1
    description: Artifact metadata and bytes are immutable, contained, restart-safe, and verified by declared length and SHA-256
    requirement: ART-01
    verification:
      - kind: unit
        ref: "tests/storage/test_artifacts.py (16 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over Artifact custody and tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Every staged/published/metadata crash state recovers idempotently to removed, quarantined, verified, or explicitly unavailable custody
    requirement: ART-01, STO-01
    verification:
      - kind: integration
        ref: "tests/storage/test_artifact_recovery.py (8 passed)"
        status: pass
      - kind: other
        ref: "Artifact suites plus architecture hygiene (29 passed)"
        status: pass
    human_judgment: false
duration: 25min
completed: 2026-08-05
status: complete
---

# Phase 30 Plan 04: Immutable Artifact Custody and Recovery Summary

**Artifact metadata and bytes now have immutable, hash-verified local custody plus deterministic recovery for every filesystem/SQLite split state.**

## Accomplishments

- Added metadata-only, empty-byte, and large-blob Artifact persistence with exact content type, metadata, length, and SHA-256 behavior.
- Added safe single-component identity validation, contained relative blob paths, symlink refusal, and no-overwrite publication.
- Added identical reuse idempotency, conflicting identity rejection, explicit unavailable state, and fail-closed missing/corrupt reads.
- Added named crash points after staging, after publish, before metadata commit, and after metadata commit.
- Added idempotent recovery that removes abandoned stages, quarantines published orphans, verifies committed pairs, and marks broken custody unavailable.

## Task Commits

1. **Immutable Artifact custody** — `4d8d9a1`
2. **Deterministic Artifact recovery** — `381ac1d`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Correctness] Made recovery time explicit**

- Implemented `recover(unavailable_at)` instead of an implicit clock read so unavailable facts retain the phase-wide rule that every timestamp enters as a validated dependency.

## Self-Check: PASSED

- Artifact custody tests: 16 passed.
- Crash and recovery tests: 8 passed.
- Combined Artifact and architecture suite: 29 passed.
- Strict mypy, Ruff, format, and `git diff --check`: passed.
- Artifacts: 3/3; key links: 2/2.

## Next Plan Readiness

Artifact custody is ready for Engine facts, Check evidence, document workers, and portable Bundles.

---
*Phase: 30-durable-storage-artifacts-and-leases*
*Completed: 2026-08-05*
