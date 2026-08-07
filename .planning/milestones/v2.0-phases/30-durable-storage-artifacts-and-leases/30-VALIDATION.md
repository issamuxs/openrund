---
phase: 30
slug: durable-storage-artifacts-and-leases
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for durable local custody and coordination.

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Config file | `pyproject.toml` |
| Quick run command | `uv run --python 3.12 pytest tests/storage tests/ports -q` |
| Full suite command | `uv run --python 3.12 pytest -q` |
| Estimated runtime | under 60 seconds before stress repetition |

## Sampling Rate

- After every task commit: run the task's named focused pytest command.
- After every plan wave: run all `tests/storage` and `tests/ports` tests plus strict mypy/Ruff on changed files.
- Before verification: run compatibility, concurrency, crash injection, full pytest, strict mypy, Ruff, lock, and build gates.
- Maximum focused-test feedback latency: 30 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---:|---:|---|---|---|---|---|---|---|
| 30-01-01 | 01 | 1 | EVT-01, ART-01, STO-02 | T-30-RACE / T-30-CORRUPT | corrected immutable storage contracts | contract | `uv run --python 3.12 pytest tests/ports/test_store_protocols.py tests/ports/test_memory_stores.py -q` | ✅ | ✅ green |
| 30-01-02 | 01 | 1 | STO-01 | T-30-PARTIAL / T-30-LEAK | versioned migrations and safe SQLite boundary | unit/integration | `uv run --python 3.12 pytest tests/storage/test_database.py -q` | ✅ | ✅ green |
| 30-02-01 | 02 | 2 | EVT-01, STO-01 | T-30-RACE / T-30-CORRUPT | expected-position append and contiguous reads | integration | `uv run --python 3.12 pytest tests/storage/test_events.py -q` | ✅ | ✅ green |
| 30-02-02 | 02 | 2 | STO-01 | T-30-RACE / T-30-BUSY | atomic multi-Run writes and bounded contention | concurrency | `uv run --python 3.12 pytest tests/storage/test_event_concurrency.py -q` | ✅ | ✅ green |
| 30-03-01 | 03 | 3 | EVT-01 | T-30-PARTIAL | observer failure follows committed success | unit/integration | `uv run --python 3.12 pytest tests/storage/test_event_log.py -q` | ✅ | ✅ green |
| 30-04-01 | 04 | 2 | ART-01, STO-01 | T-30-PATH / T-30-OVERWRITE / T-30-CORRUPT | immutable staged bytes and exact metadata | integration | `uv run --python 3.12 pytest tests/storage/test_artifacts.py -q` | ✅ | ✅ green |
| 30-04-02 | 04 | 3 | ART-01, STO-01 | T-30-PARTIAL / T-30-CORRUPT | crash recovery classifies every mismatch | fault injection | `uv run --python 3.12 pytest tests/storage/test_artifact_recovery.py -q` | ✅ | ✅ green |
| 30-05-01 | 05 | 2 | STO-02 | T-30-RACE / T-30-AUTHORITY | fenced conditional Lease semantics | concurrency | `uv run --python 3.12 pytest tests/storage/test_leases.py -q` | ✅ | ✅ green |
| 30-06-01 | 06 | 1 | STO-02 | T-30-PATH / T-30-AUTHORITY | contained deterministic Run-home layout | unit/integration | `uv run --python 3.12 pytest tests/storage/test_layout.py -q` | ✅ | ✅ green |
| 30-07-01 | 07 | 4 | EVT-01, ART-01, STO-01, STO-02 | T-30-COMPAT / T-30-EVIDENCE | authenticated schema/row compatibility | compatibility | `uv run --python 3.12 pytest tests/storage/test_compatibility.py -q` | ✅ | ✅ green |
| 30-07-02 | 07 | 4 | EVT-01, ART-01, STO-01, STO-02 | all | API/authority/security fences, installed typing, and release quality | architecture/release | `uv run --python 3.12 pytest -q && uv run --python 3.12 mypy --strict src/openrund tests && uv run ruff check src tests && uv run ruff format --check src tests && uv lock --check && uv build` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [x] `tests/storage/conftest.py` — temporary database/artifact roots and typed factories.
- [x] `tests/storage/test_database.py` — migration and connection-policy coverage.
- [x] `tests/storage/test_events.py` — Event custody behavior coverage.
- [x] `tests/storage/test_event_concurrency.py` — deterministic writer/busy coordination harness.
- [x] `tests/storage/test_event_log.py` — post-commit observer harness.
- [x] `tests/storage/test_artifacts.py` — immutable metadata/blob cases.
- [x] `tests/storage/test_artifact_recovery.py` — named fault checkpoints and reopen harness.
- [x] `tests/storage/test_leases.py` — time/token factories and concurrent acquire harness.
- [x] `tests/storage/test_layout.py` — unsafe component and symlink fixtures.
- [x] `tests/storage/test_compatibility.py` — authenticated SQLite evidence copier.
- [x] `tests/storage/test_hygiene.py` — import, method-surface, and secret-safe error fences.

Existing pytest, asyncio execution, strict mypy, Ruff, package build, and installed-typing infrastructure require no new dependency.

## Manual-Only Verifications

All Phase 30 behaviors have automated verification. No UI or visual verification applies.

## Validation Sign-Off

- [x] Every planned task has a deterministic automated command or Wave 0 target.
- [x] Sampling continuity has no three-task gap.
- [x] Wave 0 names every missing test surface.
- [x] No watch-mode flags or fixture-update commands are used.
- [x] Feedback target is under 30 seconds for focused tests.
- [x] `nyquist_compliant: true` is set.

**Approval:** approved for planning 2026-08-05

**Execution:** complete 2026-08-05 — 625 tests and all release gates green after review fixes.

## Validation Audit 2026-08-05

| Metric | Count |
|---|---:|
| Requirements audited | 4 |
| Tasks audited | 11 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All four Phase 30 requirements have direct automated behavioral, integration, compatibility, architecture, typing, and release coverage. No manual-only validation remains.
