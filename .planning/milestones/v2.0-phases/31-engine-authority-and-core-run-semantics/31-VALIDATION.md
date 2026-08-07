---
phase: 31
slug: engine-authority-and-core-run-semantics
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 31 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Config file | `pyproject.toml` |
| Quick run command | `uv run --python 3.12 pytest tests/engine -q` |
| Full suite command | `uv run --python 3.12 pytest -q` |
| Feedback target | under 30 seconds for focused tests |

## Sampling Rate

- After each task: run its named focused test and strict typing command.
- After each wave: run all `tests/engine` plus affected contract/codec/View/storage tests.
- Before phase verification: run compatibility, concurrency, architecture, installed typing, full pytest, mypy, Ruff, lock, and build gates.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure behavior | Automated command | Status |
|---|---:|---:|---|---|---|---|
| 31-01-01 | 01 | 1 | ENG-01, RUN-01, MSG-01 | typed runtime operations and narrow Engine dependencies | `pytest tests/engine/test_contracts.py` | ✅ green |
| 31-01-02 | 01 | 1 | ENG-02 | one canonical Content hash boundary | `pytest tests/engine/test_records.py` | ✅ green |
| 31-02-01 | 02 | 2 | ENG-01, RUN-01 | pure lifecycle and blocker legality | `pytest tests/engine/test_legality.py` | ✅ green |
| 31-02-02 | 02 | 2 | ENG-02 | exact decision records for all branches | `pytest tests/engine/test_records.py` | ✅ green |
| 31-03-01 | 03 | 3 | ENG-01, ENG-02 | complete replay and atomic decision append | `pytest tests/engine/test_engine.py` | ✅ green |
| 31-03-02 | 03 | 3 | ENG-01, ENG-02 | race retry and durable idempotency | `pytest tests/engine/test_concurrency.py` | ✅ green |
| 31-04-01 | 04 | 4 | RUN-01 | lawful Run bootstrap and terminal behavior | `pytest tests/engine/test_run_lifecycle.py` | ✅ green |
| 31-04-02 | 04 | 4 | RUN-01 | exhaustive completion blocker evidence | `pytest tests/engine/test_completion.py` | ✅ green |
| 31-05-01 | 05 | 5 | MSG-01 | Message and ModelCall transition legality | `pytest tests/engine/test_model_lifecycle.py` | ✅ green |
| 31-05-02 | 05 | 5 | MSG-01 | failure classification remains distinct | `pytest tests/engine/test_model_failures.py` | ✅ green |
| 31-06-01 | 06 | 6 | ENG-01, MSG-01 | proposals route through Command authority | `pytest tests/engine/test_proposals.py` | ✅ green |
| 31-06-02 | 06 | 6 | ENG-01, ENG-02 | no public authority bypass | `pytest tests/engine/test_hygiene.py` | ✅ green |
| 31-07-01 | 07 | 7 | all | frozen command/Event compatibility | `pytest tests/engine/test_compatibility.py` | ✅ green |
| 31-07-02 | 07 | 7 | all | complete release boundary | full release command in plan | ✅ green |

The plan commands use `uv run --python 3.12` and include strict mypy where types change.

## Wave 0 Requirements

- [x] `tests/engine/conftest.py` — deterministic Engine dependency and Event builders.
- [x] `tests/engine/test_contracts.py` — new operation and Engine value validation.
- [x] `tests/engine/test_records.py` — decision record and hash mapping.
- [x] `tests/engine/test_legality.py` — pure lifecycle matrix.
- [x] `tests/engine/test_engine.py` — core submit pipeline.
- [x] `tests/engine/test_concurrency.py` — deterministic conflict/retry harness.
- [x] `tests/engine/test_run_lifecycle.py` — bootstrap and terminal scenarios.
- [x] `tests/engine/test_completion.py` — every completion blocker class.
- [x] `tests/engine/test_model_lifecycle.py` — Message and ModelCall transitions.
- [x] `tests/engine/test_model_failures.py` — provider/transport/parse/legality split.
- [x] `tests/engine/test_proposals.py` — untrusted proposal path.
- [x] `tests/engine/test_compatibility.py` — authenticated frozen evidence.
- [x] `tests/engine/test_hygiene.py` — authority/import/API/installed typing gates.

Existing async pytest support, memory/SQLite stores, frozen fixture loader, build checks, and installed-typing harness require no new dependency.

## Manual-Only Verifications

None. OpenRund has no graphical UI, and every Phase 31 interaction is a Python API behavior with automated evidence.

## Validation Sign-Off

- [x] Every planned task has an automated verification target.
- [x] No three-task sampling gap exists.
- [x] Wave 0 names every missing test surface.
- [x] No fixture-update or watch-mode command is part of verification.
- [x] `nyquist_compliant: true` is set.

**Approval:** approved for autonomous planning 2026-08-05

**Execution:** complete 2026-08-05 — 676 tests and all release gates green after the review fix.

## Validation Audit 2026-08-05

| Metric | Count |
|---|---:|
| Requirements audited | 4 |
| Tasks audited | 14 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

ENG-01, ENG-02, RUN-01, and MSG-01 each have direct automated contract, behavioral, concurrency, recovery, compatibility, architecture, installed-typing, and release coverage. No manual-only validation remains.
