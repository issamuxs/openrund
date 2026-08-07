---
phase: 36-local-assembly-cli-and-flagship-demo
verified: 2026-08-06T21:30:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 36 Verification — Local Assembly, CLI, and Flagship Demo

## Verdict

**Passed.** Python users can assemble, invoke, inspect, control, and demonstrate
the complete governed runtime through stable installed-package surfaces.
CLI-01, DEMO-01, DX-09, and DX-10 are satisfied.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Explicit local assembly wires custody, Engine, built-ins, provider loop, operator input, and reporting without implicit roots or Authority. | VERIFIED | Assembly construction, lifetime, symlink, reporting, explicit-builtin, and empty-default tests pass. |
| 2 | The top-level Python API is deliberate, typed, installed, and protected from accidental expansion. | VERIFIED | Exact allowlist, import direction, private testing, wheel content, and installed-consumer mypy tests pass. |
| 3 | The installed CLI covers control, inspection, Waits, evidence, Checks, Artifacts, and every Bundle operation with stable output/exits and Engine legality. | VERIFIED | CLI command, parity, determinism, rejection, integrity, and architecture suites pass. |
| 4 | One installed offline demonstration proves every required governance and portability boundary. | VERIFIED | Deterministic source and isolated-wheel console demonstrations pass with all four built-ins and full `.orun` lifecycle. |

## Automated Evidence

| Check | Result |
|---|---|
| Full Python suite | PASS — 963 passed, 3 opt-in live checks skipped |
| Strict mypy | PASS — 219 source/test files |
| Ruff lint and format | PASS — 219 files |
| Lockfile and distributions | PASS |
| Installed-wheel typing and console demo | PASS |
| Documentation and links | PASS |
| Plan completeness | PASS — 6 plans, 6 summaries |
| Standard-depth code review | PASS — final report clean |
| Security audit | PASS — 10 threats closed, 0 open |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| CLI-01 | SATISFIED | Installed command matrix, typed parity, deterministic text/JSON, stable exits, and Engine-only mutation. |
| DEMO-01 | SATISFIED | Installed deterministic governed-coding workflow covers all required lifecycle facts. |
| DX-09 | SATISFIED | Explicit injectable assembly with safe empty defaults and controlled resource lifetime. |
| DX-10 | SATISFIED | Exact public imports and installed typing protected by source and wheel tests. |

## Gaps

None.
