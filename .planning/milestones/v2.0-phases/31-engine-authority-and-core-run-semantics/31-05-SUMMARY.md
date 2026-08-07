---
phase: 31-engine-authority-and-core-run-semantics
plan: "05"
subsystem: model-lifecycle
tags: [python, engine, messages, model-calls, providers]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Authoritative submit path and Event materialization
provides:
  - Replayable Message add/delta lifecycle with exact Command linkage
  - Single-start/single-terminal ModelCall lifecycle
  - Stable provider, transport, and parse failure classifications
affects: [provider-adapters, durable-model-loop, proposals]
tech-stack:
  added: []
  patterns: [entity-state history reduction, stable failure enum, separate runtime failure commands]
key-files:
  created:
    - tests/engine/test_model_lifecycle.py
    - tests/engine/test_model_failures.py
  modified:
    - src/openrund/contracts/commands.py
    - src/openrund/codec/_decisions.py
    - src/openrund/codec/_events.py
key-decisions:
  - "Restrict Engine-origin ModelCall failure classification to provider, transport, or parse while retaining broader historical Event decoding."
  - "Allow declaration-only supersession to be encoded only inside command.recorded Events; standalone decision encoding keeps its frozen writer guard."
requirements-completed: [MSG-01]
duration: 12min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 05: Message and ModelCall Lifecycle Summary

**Messages and model interactions now have one replayable, command-linked lifecycle with mechanically distinct failure layers.**

## Accomplishments

- Proved Message creation and delta linkage, including unknown-Message rejection without target Events.
- Proved ModelCall start uniqueness, terminal preconditions, and exactly one completed/failed/cancelled outcome.
- Added stable provider, transport, and parse failure classifications for runtime-origin failure Commands.
- Closed the supersession codec path so durable Event evidence is writable and readable while standalone declaration evidence remains guarded.

## Task Commits

1. **Supersession Event codec closure** — `32500f6`
2. **Message and ModelCall lifecycle** — `a3e9359`
3. **Failure classification boundaries** — `7d007c9`

## Deviations from Plan

### Auto-fixed Issues

- Completing the idempotency path exposed that command.recorded supersession was writer-enabled semantically but still rejected by the Event codec and initial payload shape validator. The codec now permits this exact Event context without weakening standalone declaration-only rules.

## Self-Check: PASSED

- Engine and complete codec suites: 108 passed.
- Strict mypy: passed across contracts, codec, Engine, and tests.
- Ruff lint/format and `git diff --check`: passed.

## Next Plan Readiness

Ready for Plan 31-06 untrusted ModelProposal adaptation and authority-boundary hygiene.
