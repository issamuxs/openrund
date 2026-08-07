---
phase: 29
slug: deterministic-views-and-replay-facts
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 29 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Quick command | `uv run --python 3.12 pytest tests/views -q` |
| Full command | `uv run --python 3.12 pytest -q && uv run --python 3.12 mypy --strict src/openrund tests && uv run ruff check src tests && uv run ruff format --check src tests && uv lock --check && uv build` |
| Frozen evidence | 71 authenticated View rows in `tests/fixtures/compatibility/v1/manifest.json` |

## Sampling Rate

- After each task: named reducer test plus strict mypy on the changed source/test files.
- After each wave: complete `tests/views` plus full strict mypy and Ruff.
- Before phase verification: exact 71-case corpus, determinism/hygiene, installed typing, full suite, lock, and build.
- No snapshot-update, fixture-write, predecessor-execution, UI, or CLI commands.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat | Test | Automated command | Status |
|---|---:|---:|---|---|---|---|---|
| 29-01-01 | 01 | 1 | VIEW-01 | T-29-HISTORY | Known/incomplete replay model and exact watermark validation | `uv run --python 3.12 pytest tests/views/test_history.py -q` | green |
| 29-01-02 | 01 | 1 | VIEW-01 | T-29-CORPUS | Authenticated exact 71-row View fixture selection | `uv run --python 3.12 pytest tests/views/test_fixture_integrity.py -q` | green |
| 29-02-01 | 02 | 2 | VIEW-01 | T-29-ORDER | Timeline and Artifact index reducers | `uv run --python 3.12 pytest tests/views/test_timeline_artifacts.py -q` | green |
| 29-02-02 | 02 | 2 | VIEW-01 | T-29-EXPLAIN | Checkpoint correction and Report reducers | `uv run --python 3.12 pytest tests/views/test_checkpoints_reports.py -q` | green |
| 29-03-01 | 03 | 2 | VIEW-01 | T-29-ACTION | Action status and reconciliation reducers | `uv run --python 3.12 pytest tests/views/test_actions.py -q -k 'status or reconciliation'` | green |
| 29-03-02 | 03 | 2 | VIEW-01 | T-29-RECEIPT | Immutable complete Action Receipts | `uv run --python 3.12 pytest tests/views/test_actions.py -q` | green |
| 29-04-01 | 04 | 3 | VIEW-01 | T-29-WAIT | Five-kind pending and terminal Wait queue reduction | `uv run --python 3.12 pytest tests/views/test_waits.py -q` | green |
| 29-05-01 | 05 | 3 | VIEW-01 | T-29-DELEGATION | Delegated-run lifecycle and handoff state | `uv run --python 3.12 pytest tests/views/test_delegation.py -q -k 'lifecycle or handoff'` | green |
| 29-05-02 | 05 | 3 | VIEW-01 | T-29-JOIN | all/any/quorum join facts without parent mutation | `uv run --python 3.12 pytest tests/views/test_delegation.py -q` | green |
| 29-06-01 | 06 | 4 | VIEW-01 | T-29-STATUS | Run lifecycle, Authority, and check summaries | `uv run --python 3.12 pytest tests/views/test_run_status.py -q -k 'status or authority or check'` | green |
| 29-06-02 | 06 | 4 | VIEW-01 | T-29-READINESS | Ordered readiness blockers remain explanatory | `uv run --python 3.12 pytest tests/views/test_run_status.py -q` | green |
| 29-07-01 | 07 | 5 | VIEW-01 | T-29-MATRIX | Aggregate rebuild matches all 71 frozen View rows | `uv run --python 3.12 pytest tests/views/test_view_corpus.py -q` | green |
| 29-07-02 | 07 | 5 | VIEW-01 | T-29-AUTH | Determinism, prefix equivalence, import/method fences, full gate | `uv run --python 3.12 pytest tests/views/test_view_determinism.py tests/views/test_view_hygiene.py -q` | green |

## Wave 0 Requirements

- [x] `tests/views/conftest.py` authenticates View evidence before decode.
- [x] `tests/views/test_fixture_integrity.py` enforces exact counts, containment, hashes, and no mutation.
- [x] `src/openrund/views/` exists with a typed incomplete/complete replay boundary.

## Manual Verification

None. All success criteria are machine-testable.

## Sign-Off

- [x] Every executable task has an automated command.
- [x] All three roadmap success criteria and VIEW-01 are covered.
- [x] Incomplete-watermark and no-authority behavior are tested as first-class security properties.
- [x] UI and CLI workflows are absent.
