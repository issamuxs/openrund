# Phase 37 Retirement Qualification

**Qualified:** 2026-08-04
**Status:** Passed
**Scope:** RET-01 through RET-10

## Immutable gate evidence

The Python retirement test authenticates every gate record through the frozen
manifest path, byte length, SHA-256 commitment, decoded meaning, decision ID,
and provenance inventory key. Each gate is also mapped to executable Python
evidence that is exercised by the complete suite.

| Gate | Qualification evidence | Result |
|---|---|---|
| RET-01 | Frozen JSON, Event, and decision readers | Passed |
| RET-02 | Canonical JSON, Event, and decision writers | Passed |
| RET-03 | Complete Event replay and deterministic Views | Passed |
| RET-04 | Frozen SQLite schema and adapter behavior | Passed |
| RET-05 | Immutable Artifact storage and Bundle Artifact reads | Passed |
| RET-06 | Bundle commitments, export, verify, replay, and import | Passed |
| RET-07 | Isolated wheel install, typing probe, and console demo | Passed |
| RET-08 | Python source/distribution allowlist and release hygiene | Passed |
| RET-09 | Frozen fixture authentication and provenance retention | Passed |
| RET-10 | One authoritative Python package and implementation surface | Passed |

The executable compatibility oracle remained present and quarantined for the
entire qualification. It was not invoked by any Python test and can now be
removed while the immutable fixture corpus remains.

## Supported Python matrix

The identical repository suite, including isolated wheel and source-
distribution installations of the flagship console demo, passed on every
supported interpreter:

| Interpreter | Result |
|---|---|
| Python 3.12 | 968 passed, 3 skipped |
| Python 3.13 | 968 passed, 3 skipped |
| Python 3.14 | 968 passed, 3 skipped |

The three skips are the intentionally opt-in live-provider network checks.
All normal qualification is offline and credential-free.

## Commands

```text
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.12 pytest -q
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 pytest -q
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.14 pytest -q
```

