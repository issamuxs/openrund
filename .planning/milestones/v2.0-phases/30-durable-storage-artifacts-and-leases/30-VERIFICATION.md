---
phase: 30-durable-storage-artifacts-and-leases
verified: 2026-08-06T13:57:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 30 Verification — Durable Storage, Artifacts, and Leases

## Verdict

**Passed.** Runtime hosts now have trustworthy local custody for ordered Event history, immutable Artifact content, fenced execution coordination, and deterministic Run homes. All four roadmap success criteria and EVT-01, ART-01, STO-01, and STO-02 are verified by executable tests. No human verification, UI workflow, UI specification, or CLI implementation is required.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Hosts append immutable Events only at the expected per-Run position, receive a distinct stale-position conflict, read gap-free history, and retain durable success despite subscriber failures. | VERIFIED | Atomic expected-watermark append, whole-stream gap validation, duplicate-ID rollback, post-commit subscriber isolation, and cancellation tests pass across SQLite and port substitutes. |
| 2 | SQLite Event and Artifact custody survives migration, reopen, concurrent writers, bounded busy conditions, duplicates, injected crashes, and partial failures without weakening committed history. | VERIFIED | Versioned immediate transactions, exact schema/index validation, 32 authenticated SQLite evidence rows, concurrent writer tests, fault checkpoints, and reopen tests all pass. |
| 3 | Hosts store immutable Artifact metadata and bytes with integrity checks, reject conflicting reuse, recover blob/metadata mismatches, and explicitly represent unavailable content outside Events. | VERIFIED | Absent-only hard-link publication, descriptor-based no-follow verification, digest/length checks, immutable reuse, staged recovery, orphan quarantine, and unavailable marking are covered by deterministic tests. |
| 4 | Executors acquire, renew, release, replace, and expire scoped Leases and use deterministic configurable Run-home paths without conferring runtime Authority. | VERIFIED | Immediate-transaction one-per-Run acquisition, exact token/identity/owner fencing, strict supplied-time expiry, concurrency, symlink rejection, containment, and no-authority AST fences pass. |

**Score:** 4/4 must-haves verified.

## Required Artifacts

| Artifact | Status | Verification |
|---|---|---|
| `src/openrund/storage/_database.py` | VERIFIED | Short-lived configured connections, bounded busy policy, additive migrations, exact table/index/constraint validation, explicit immediate transactions, rollback, and safe error translation. |
| `src/openrund/storage/_events.py` and `_event_log.py` | VERIFIED | Exact Event codec custody, atomic single/multi-Run append, complete gap validation, durable reads, and isolated ordered post-commit subscribers. |
| `src/openrund/storage/_artifacts.py` | VERIFIED | Immutable SQLite metadata plus contained staged blobs, no-follow descriptor verification, recovery, quarantine, and unavailable-content handling. |
| `src/openrund/storage/_leases.py` | VERIFIED | Caller-time, injected-identity, token-fenced local execution coordination under immediate transactions. |
| `src/openrund/storage/_layout.py` | VERIFIED | Pure deterministic layout plus explicit symlink-aware contained materialization. |
| `src/openrund/storage/__init__.py` | VERIFIED | Exact typed public adapter/recovery/layout surface with no infrastructure or Authority exports. |
| `tests/storage/` and installed-package tests | VERIFIED | Compatibility, migration, crash, concurrency, hygiene, typing, packaging, and full release coverage. |

## Key-Link Verification

| Link | Status | Evidence |
|---|---|---|
| Public storage adapters → typed Event, Artifact, and Lease ports | WIRED | Strict mypy and installed-wheel consumer checks assign each adapter to its structural protocol and exercise async result types. |
| Event adapter → canonical codec → authenticated persisted rows | WIRED | New writes use exact codec payloads; reads preserve nullable links, narrowly normalize the authenticated stored creation payload, and leave SQLite rows unchanged. |
| Artifact metadata → relative blob reference → contained immutable bytes | WIRED | SQLite stores only `blobs/<id>.blob`; open/fstat/digest checks verify the exact descriptor without following symlinks. |
| Public async methods → private synchronous transaction/file operations | WIRED | AST hygiene proves no SQLite connection or transaction spans an await; the private kernel owns open/begin/commit/rollback/close. |
| Compatibility manifest → exact SQLite inventory → temporary database proof | WIRED | All 32 selected evidence files are contained, regular, length/hash authenticated, consumed exactly once, and unchanged after tests. |

## Automated Evidence

| Check | Result |
|---|---|
| Authenticated SQLite compatibility | PASS — 32/32 evidence rows; 4 tests |
| Storage architecture/security hygiene | PASS — 5/5 |
| Focused post-review regressions | PASS — 52 passed |
| Full Python suite | PASS — 625 passed |
| Milestone regression suite after downstream integration | PASS — 972 passed, 3 opt-in live-provider checks skipped |
| Strict mypy | PASS — 96 source files |
| Ruff lint and format | PASS — 96 files |
| Lockfile validation | PASS |
| Wheel and source distribution | PASS |
| Installed-wheel strict consumer and isolated import | PASS |
| Plan completeness | PASS — 7 plans, 7 summaries |
| Final-plan artifact verification | PASS — 3/3 |
| Final-plan key-link verification | PASS — 2/2 |
| Standard-depth code review | PASS — three first-pass integrity findings fixed; final report clean |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| EVT-01 | SATISFIED | Expected-position immutable commits, gap-free reads, and observer failure isolation are durable and tested. |
| ART-01 | SATISFIED | Metadata and bytes are immutable, integrity-checked, recoverable, and kept outside Event payloads. |
| STO-01 | SATISFIED | Real SQLite adapters pass migration, reopen, concurrency, bounded busy, duplicate, crash, compatibility, and packaging gates. |
| STO-02 | SATISFIED | Scoped fenced Leases and deterministic contained Run-home paths are implemented without Authority semantics. |

## Anti-Patterns and Human Verification

- No human-only verification is required; every success criterion is machine-testable and passed.
- No graphical UI, UI-SPEC, or visual-review artifact exists. CLI interaction remains assigned to ordinary Phase 36 plans and tests.
- Storage contains no Engine legality, Authority grant/revoke, provider, capability, Bundle, CLI, or UI dependency or public method.
- No overrides were applied.

## Gaps

None.
