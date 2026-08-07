---
phase: 33
slug: capability-runtime-actions-and-built-ins
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 33 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Config file | `pyproject.toml` |
| Quick run command | `uv run --python 3.12 pytest tests/capabilities -q` |
| Full suite command | `uv run --python 3.12 pytest -q` |
| Feedback target | under 30 seconds for focused tests |

## Sampling Rate

- Run each plan's focused pytest, typing, and lint commands immediately after implementation.
- Run Engine plus capability tests after Action lifecycle changes and after all subprocess built-ins.
- Before closure, run full pytest, strict mypy, Ruff, lock, build, installed-wheel worker/typing, docs, compatibility, security, and diff gates.

## Per-Task Verification Map

| Plan | Requirement | Secure behavior | Automated target | Status |
|---:|---|---|---|---|
| 33-01 | CAP-01 | closed definitions, registry, schema, result codec, transports | `tests/capabilities/test_registry.py test_transports.py` | ✅ green |
| 33-02 | ACT-01 | durable start, exact terminal, Artifact custody, ambiguity | `tests/capabilities/test_action_runner.py` | ✅ green |
| 33-03 | BUILTIN-01 | bounded read/list/stat and symlink confinement | `tests/capabilities/test_filesystem_read.py` | ✅ green |
| 33-04 | BUILTIN-01 | hash/overwrite/atomic mutation protections | `tests/capabilities/test_filesystem_mutation.py` | ✅ green |
| 33-05 | BUILTIN-02 | root-bound Markdown stdio worker operations | `tests/capabilities/test_documents.py` | ✅ green |
| 33-06 | BUILTIN-03 | allowlisted process env/time/output/cancel limits | `tests/capabilities/test_process.py` | ✅ green |
| 33-07 | BUILTIN-03 | fixed local git verbs and no remote/credentials | `tests/capabilities/test_git.py` | ✅ green |
| 33-08 | all | Engine integration, hygiene, typing, docs, package | `tests/capabilities/test_integration.py test_hygiene.py` plus release gate | ✅ green |

## Wave 0 Requirements

- [x] Registry and schema boundary tests.
- [x] Strict in-process/stdio transport tests.
- [x] Action lifecycle and Artifact materialization tests.
- [x] Filesystem read adversarial tests.
- [x] Filesystem mutation adversarial tests.
- [x] Markdown worker protocol and operation tests.
- [x] Process boundary/cancellation tests.
- [x] Local git verb/security tests.
- [x] Capability integration, compatibility, hygiene, and installed-wheel tests.

## Manual-Only Verifications

None. Every interaction in this phase is a Python API or subprocess protocol behavior and must have automated evidence.

## Validation Sign-Off

- [x] Every planned responsibility has an automated verification target.
- [x] No three-task sampling gap exists.
- [x] No fixture generation or watch mode is a verification command.
- [x] Graphical UI checks are absent because the project has no graphical UI.

**Approval:** approved for autonomous planning 2026-08-05

**Completion:** 827 tests, strict typing, lint, format, lock, build, installed-wheel, compatibility, review, and security evidence verified 2026-08-05.
