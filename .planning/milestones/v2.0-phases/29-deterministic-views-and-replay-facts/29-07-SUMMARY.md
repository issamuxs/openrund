---
phase: 29-deterministic-views-and-replay-facts
plan: "07"
subsystem: aggregate-view-replay
tags: [replay, compatibility, determinism, immutability, packaging]
requires:
  - phase: 29-01-known-history
    provides: Fail-closed exact-watermark validation
  - phase: 29-02-through-29-06
    provides: All focused immutable reducers
provides:
  - One aggregate rebuild_views entry point
  - Complete immutable RunViewBundle
  - Exact 71-row authenticated compatibility gate
  - Fresh-process determinism and no-authority gates
affects: [storage-replay, engine-inspection, bundles, cli-inspection]
tech-stack:
  added: []
  patterns: [validate-before-reduce, one-pass composed immutable bundle]
key-files:
  created:
    - src/openrund/views/_rebuild.py
    - tests/views/test_view_corpus.py
    - tests/views/test_view_determinism.py
    - tests/views/test_view_hygiene.py
  modified:
    - src/openrund/views/__init__.py
    - src/openrund/views/_model.py
    - tests/package/test_installed_typing.py
key-decisions:
  - "Validate the exact watermark before invoking any focused reducer and return no bundle on incomplete history."
  - "Keep historical schema lifting and v1 output projection entirely in authenticated tests; production decoding stays strict and semantic Views remain snake_case."
  - "Compose Actions, Artifacts, and Waits once and inject their immutable results into Run-status readiness."
  - "Expose only replay values and rebuild functions; no View type can append, submit, resolve, approve, authorize, or decide legality."
patterns-established:
  - "Compatibility is tested through an explicit test-only projection rather than adding wire aliases to semantic values."
  - "Fresh-instance, fresh-process, prefix, and irrelevant-replay equality all gate deterministic reconstruction."
requirements-completed: [VIEW-01]
coverage:
  - id: D1
    description: Aggregate replay reproduces all 71 authenticated frozen View results exactly
    requirement: VIEW-01
    verification:
      - kind: integration
        ref: "tests/views/test_view_corpus.py (71 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: Replay is fail-closed, immutable, deterministic, packaged, and non-authoritative
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_view_determinism.py and test_view_hygiene.py (10 passed)"
        status: pass
      - kind: other
        ref: "Views suite (123 passed), full suite (538 passed), strict mypy, Ruff, lock, build, installed typing"
        status: pass
    human_judgment: false
duration: 22m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 07: Aggregate Replay and Release Gates Summary

**One fail-closed Python entry point now rebuilds every immutable View surface, matching all 71 frozen results exactly.**

## Accomplishments

- Added `RunViewBundle` and `rebuild_views()` with validation before any reducer invocation.
- Composed Run status/readiness, timeline, Actions, Waits, Artifacts, Checkpoints, Delegation, and Reports.
- Added an explicit test-only v1 compatibility projection covering all 71 authenticated rows.
- Added repeated, prefix, cache-independence, fresh-process, immutability, dependency, API, and no-authority gates.
- Extended installed-wheel strict typing coverage to the View replay API.

## Task Commits

1. **Aggregate replay and exact compatibility** — `425e243`
2. **Determinism, authority, and installed typing gates** — `e10631c`

## Deviations from Plan

Historical View streams contain minimal Wait, join, and Check payloads that predate the stricter semantic schema. The exact gate adds required placeholders only inside test decoding, then compares the typed Python bundle through an explicit test-only v1 projection. Production codecs and View types remain strict and contain no historical aliases.

## Self-Check: PASSED

- Exact compatibility: 71/71 passed.
- Views suite: 123 passed.
- Full suite: 538 passed.
- Strict mypy and Ruff: passed.
- Lockfile: consistent.
- Source distribution and wheel: built successfully.
- Frozen corpus integrity: 3/3 passed.
- Artifacts: 3/3; key links: 2/2.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
