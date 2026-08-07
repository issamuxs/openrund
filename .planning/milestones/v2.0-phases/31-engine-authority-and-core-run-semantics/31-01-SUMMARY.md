---
phase: 31-engine-authority-and-core-run-semantics
plan: "01"
subsystem: engine-contracts
tags: [python, engine, commands, codec, authority]
requires:
  - phase: 28-python-contract-kernel
    provides: Typed Commands, Content, IDs, Events, codecs, and runtime ports
provides:
  - Distinct validated runtime-only operations for Run, Message, and ModelCall lifecycle
  - Narrow immutable Engine dependency assembly
  - Codec-owned canonical Content bytes and SHA-256 commitments
affects: [phase-31-legality, phase-31-engine, command-evidence]
tech-stack:
  added: []
  patterns: [frozen runtime operations, narrow dependency value, codec-owned canonical hashing]
key-files:
  created:
    - src/openrund/codec/_content.py
    - src/openrund/engine/__init__.py
    - src/openrund/engine/_model.py
    - tests/engine/conftest.py
    - tests/engine/test_contracts.py
    - tests/engine/test_records.py
  modified:
    - src/openrund/contracts/commands.py
    - src/openrund/codec/__init__.py
key-decisions:
  - "Keep runtime-only lifecycle operations outside ModelOperation so provider proposals cannot construct runtime authority transitions."
  - "Keep Phase 31 Engine dependencies limited to Event custody, time, Event IDs, Message IDs, and a bounded conflict retry policy."
  - "Commit Command Content through the exact codec-owned v1 semantic encoder and canonical JSON renderer."
requirements-completed: []
duration: 10min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 01: Engine Contracts and Content Commitments Summary

**The Python kernel now distinguishes untrusted model operations from trusted runtime lifecycle intents and gives every future Command one canonical Content commitment.**

## Accomplishments

- Added frozen bootstrap/start, Message delta, and ModelCall start/complete/fail/cancel operations with strict validation.
- Preserved `ModelOperation` as the provider-safe subset while extending `CommandOperation` for Engine-origin runtime transitions.
- Added a minimal immutable Engine dependency value without provider, capability, assembly, CLI, or UI responsibilities.
- Added canonical Content bytes and lowercase SHA-256 helpers inside the codec boundary, preserving aliases, omissions, nulls, Unicode, signed zero, and UTF-16 key ordering.

## Task Commits

1. **Core Engine command contracts** — `95defdb`
2. **Canonical command Content commitments** — `1b88e62`

## Deviations from Plan

None.

## Self-Check: PASSED

- Focused and affected contract suites: 23 passed.
- Strict mypy: passed for all touched source and tests.
- Ruff lint/format and `git diff --check`: passed.
- Runtime-only ModelProposal rejection and canonical frozen-style hashes are directly tested.

## Next Plan Readiness

Ready for Plan 31-02 pure legality and durable decision-record construction.
