---
phase: 32
slug: governed-coordination-and-recovery
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 32 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Config file | `pyproject.toml` |
| Quick run command | `uv run --python 3.12 pytest tests/engine -q` |
| Full suite command | `uv run --python 3.12 pytest -q` |
| Feedback target | under 30 seconds for focused tests |

## Sampling Rate

- After each task: run its named focused pytest and strict typing command.
- After each wave: run all Engine tests plus affected View/storage/codec tests.
- Before verification: run compatibility, concurrency, atomic Delegation, architecture, installed typing, full pytest, mypy, Ruff, lock, and build gates.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure behavior | Automated command | Status |
|---|---:|---:|---|---|---|---|
| 32-01-01 | 01 | 1 | all | typed coordination/recovery operations and exact factories | `pytest tests/engine/test_coordination_contracts.py` | ✅ green |
| 32-01-02 | 01 | 1 | GOV-01 | immutable trusted governance context and fail-closed schema rules | `pytest tests/engine/test_governance.py -k context` | ✅ green |
| 32-02-01 | 02 | 2 | WAIT-01 | five Wait kinds open through Engine only | `pytest tests/engine/test_wait_lifecycle.py -k open` | ✅ green |
| 32-02-02 | 02 | 2 | WAIT-01 | exact-once resolution/cancel/expiry and timer boundaries | `pytest tests/engine/test_wait_lifecycle.py` | ✅ green |
| 32-03-01 | 03 | 3 | GOV-01, WAIT-02 | hard Action legality precedes policy/approval | `pytest tests/engine/test_governance.py` | ✅ green |
| 32-03-02 | 03 | 3 | WAIT-02 | approval resolution and current-state resumption | `pytest tests/engine/test_approval.py` | ✅ green |
| 32-04-01 | 04 | 4 | ACT-02 | explicit unknown outcome and evidence-backed reconciliation | `pytest tests/engine/test_recovery.py` | ✅ green |
| 32-04-02 | 04 | 4 | CHK-01 | Checks, Checkpoints, Annotations, and non-authority boundaries | `pytest tests/engine/test_checks.py` | ✅ green |
| 32-05-01 | 05 | 5 | DEL-01, GOV-01 | bounded Delegation contract and lineage legality | `pytest tests/engine/test_delegation.py -k legality` | ✅ green |
| 32-05-02 | 05 | 5 | DEL-01 | atomic parent/child establishment and conflict recovery | `pytest tests/engine/test_delegation.py` | ✅ green |
| 32-06-01 | 06 | 6 | DEL-01, WAIT-01 | explicit terminal handoff and all/any/quorum joins | `pytest tests/engine/test_delegation_lifecycle.py -k 'handoff or join'` | ✅ green |
| 32-06-02 | 06 | 6 | DEL-01, GOV-01 | parent cancellation and late-handoff policy | `pytest tests/engine/test_delegation_lifecycle.py` | ✅ green |
| 32-07-01 | 07 | 7 | all | authenticated Phase 32 Event compatibility | `pytest tests/engine/test_coordination_compatibility.py` | ✅ green |
| 32-07-02 | 07 | 7 | all | complete authority, packaging, docs, and release boundary | full release command in plan | ✅ green |

## Wave 0 Requirements

- [x] `tests/engine/test_coordination_contracts.py` — operation and dependency values.
- [x] `tests/engine/test_wait_lifecycle.py` — all Wait request and terminal branches.
- [x] `tests/engine/test_governance.py` — Capability/schema/Authority/policy/scope/budget/security evaluation foundation; Action evaluation expands in Plan 03.
- [x] `tests/engine/test_approval.py` — deferred Action and revalidation path.
- [x] `tests/engine/test_recovery.py` — Action unknown and reconciliation state.
- [x] `tests/engine/test_checks.py` — Check, Checkpoint, Annotation, and explanation boundaries.
- [x] `tests/engine/test_delegation.py` — contract validation and atomic establishment.
- [x] `tests/engine/test_delegation_lifecycle.py` — handoff, cancellation, late result, and joins.
- [x] `tests/engine/test_coordination_compatibility.py` — authenticated explicit evidence allowlist.
- [x] `tests/engine/test_coordination_hygiene.py` — authority/import/API/effect/interface fences.

Existing pytest, async execution, memory/SQLite atomic stores, frozen fixture loader, deterministic Views, build checks, and installed-typing harness require no new dependency.

## Manual-Only Verifications

None. Every Phase 32 interaction is a Python API behavior with automated evidence.

## Validation Sign-Off

- [x] Every planned task has an automated verification target.
- [x] No three-task sampling gap exists.
- [x] Wave 0 names every missing test surface.
- [x] No fixture-update or watch-mode command is part of verification.
- [x] `nyquist_compliant: true` is set.

**Approval:** approved for autonomous planning 2026-08-05

**Execution sign-off:** passed 2026-08-05 — 727 pytest tests, strict mypy,
Ruff lint/format, lock verification, wheel/sdist build, installed-wheel typing,
authenticated compatibility, architecture hygiene, security audit, clean code
review, and diff checks are green.
