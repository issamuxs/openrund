---
phase: 31-engine-authority-and-core-run-semantics
verified: 2026-08-05T19:41:42Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 31 Verification — Engine Authority and Core Run Semantics

## Verdict

**Passed.** Runtime hosts now govern core Run, Message, and ModelCall mutation through one Engine-owned Command path with durable decisions, exact replay facts, and concurrency-safe atomic persistence. All four roadmap success criteria and ENG-01, ENG-02, RUN-01, and MSG-01 are verified by executable tests. No human, graphical UI, or UI-specification verification is required.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Every supported mutation origin enters one Engine-owned evaluation path and supported provider, worker, storage, and inspection integrations expose no lifecycle-authority bypass. | VERIFIED | `RuntimeEngine` exposes only `submit`; every model proposal adapter delegates to it; import, method-surface, and installed-package hygiene tests pass. |
| 2 | Every committed attempt has one inspectable `command.recorded` fact with exact origin, operation, decision, trace, result, Wait, and replacement evidence; denied attempts have no target Events. | VERIFIED | Exact record-branch tests cover accepted, rejected, deferred, and superseded decisions; atomic batch tests and authenticated compatibility tests pass. |
| 3 | Hosts bootstrap, start, complete, fail, and cancel Runs lawfully; terminal mutation is rejected and every completion blocker is reported. | VERIFIED | Lifecycle matrix, terminal-state, complete-history, and exhaustive Wait/Check/Artifact/join/unknown-outcome tests pass. |
| 4 | Hosts persist and replay Message and ModelCall lifecycles, distinguish failure classes, and treat provider output only as an untrusted proposal. | VERIFIED | Message delta, ModelCall transition, provider/transport/parse/legality separation, and proposal-routing tests pass. |

**Score:** 4/4 must-haves verified.

## Required Artifacts

| Artifact | Status | Verification |
|---|---|---|
| `src/openrund/contracts/commands.py` | VERIFIED | Immutable operation, decision, trace, record, origin, and result values validate exact domain invariants. |
| `src/openrund/engine/_legality.py` | VERIFIED | Pure complete-replay legality covers bootstrap, active/terminal Runs, completion blockers, Messages, and ModelCalls without effects or ID allocation. |
| `src/openrund/engine/_engine.py` | VERIFIED | Complete history, durable duplicate recovery, stable idempotency ownership, conflict re-evaluation, and one ordered atomic append are enforced. |
| `src/openrund/engine/_records.py` and `_events.py` | VERIFIED | Exact durable decision records, canonical Content hashes, and explicit accepted target Event intents are produced. |
| `src/openrund/engine/_proposals.py` | VERIFIED | Provider proposals become inert model-origin Commands and delegate to the sole authority method. |
| `tests/engine/` and package tests | VERIFIED | Contract, legality, recovery, concurrency, lifecycle, failure, compatibility, architecture, typing, packaging, and release coverage is complete. |

## Key-Link Verification

| Link | Status | Evidence |
|---|---|---|
| Command → complete replay → pure legality | WIRED | Submit reads from position one, rejects incomplete replay, and evaluates immutable Views at the exact watermark. |
| Decision → command evidence → target Events | WIRED | Accepted IDs are allocated before record construction; one append orders `command.recorded` before every target and shares causation/Command links. |
| Expected-position conflict → re-read → re-evaluate | WIRED | Deterministic conflict tests prove an intervening terminal Event changes the retried decision to rejection. |
| Duplicate/idempotency retry → durable history | WIRED | Same Command IDs return the stored result without append; repeated key collisions all link to the original non-superseded owner. |
| ModelProposal → Command → RuntimeEngine.submit | WIRED | Proposal tests and source hygiene prove no proposal adapter appends or evaluates independently. |
| Frozen evidence → Python codecs → Engine records | WIRED | Explicit closed allowlists round-trip authenticated command/Event bytes without fixture generation. |

## Automated Evidence

| Check | Result |
|---|---|
| Focused review regression | PASS — 5 passed |
| Full Python suite | PASS — 676 passed |
| Strict mypy | PASS — 118 source/test files |
| Ruff lint and format | PASS — 118 files |
| Lockfile validation | PASS |
| Wheel and source distribution | PASS |
| Plan completeness | PASS — 7 plans, 7 summaries |
| Standard-depth code review | PASS — one first-pass recovery finding fixed; final report clean |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| ENG-01 | SATISFIED | All supported origins use one complete-replay Engine authority method with no supported lifecycle append bypass. |
| ENG-02 | SATISFIED | Exact durable evidence exists for every decision branch, with atomic target linkage and no denied target Events. |
| RUN-01 | SATISFIED | Run lifecycle, terminal protection, and exhaustive completion readiness are implemented and tested. |
| MSG-01 | SATISFIED | Message/ModelCall replay, failure separation, and untrusted proposal handling are implemented and tested. |

## Anti-Patterns and Human Verification

- No human-only verification remains.
- No graphical UI, visual-review artifact, or UI specification exists. CLI interaction remains assigned to normal Phase 36 plans and tests.
- The Engine owns no provider call loop, capability execution, Artifact custody, Lease coordination, assembly, or presentation behavior.
- No overrides were applied.

## Gaps

None.
