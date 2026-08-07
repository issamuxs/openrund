---
phase: 28-python-contract-kernel
verified: 2026-08-05T15:04:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 28 Verification — Python Contract Kernel

## Verdict

**Passed.** Python users now share one idiomatic, fully typed semantic kernel and one exact codec boundary for every downstream runtime layer. All five roadmap success criteria and all six assigned requirements are verified by executable tests. No human verification, compatibility alias, UI workflow, CLI implementation, or behavioral override is required.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Every canonical concept is kind-safe, immutable, precisely typed, fully annotated, runtime validated, and distributed with `py.typed`. | VERIFIED | Final frozen dataclasses and tagged unions cover IDs, ordered JSON, timestamps, Content, Actions, Runs, Commands, decisions, waits, delegation, Artifacts, Bundles, capabilities, and all 65 Event variants. Constructor/rejection suites pass, the built wheel contains `py.typed`, and an isolated representative consumer passes strict mypy. |
| 2 | Python semantic objects use `snake_case` while exact v1 names, aliases, presence states, and bytes remain confined to one codec boundary. | VERIFIED | Private alias registries, strict bounded decode, explicit ordered encode, canonical UTF-16 key ordering, exact number rendering, 65 Event vectors, four Command-decision vectors, and semantic hash tests all pass. AST hygiene rejects raw serialization mappings and generic dumping outside `openrund.codec`. |
| 3 | Stores, clocks, ID factories, providers, transports, and reporters are substitutable through small structural protocols and deterministic implementations. | VERIFIED | Narrow non-runtime-checkable protocols pass strict structural typing. Private in-memory stores and seeded fakes preserve insertion order, immutable observations, exact result types, and deterministic exhaustion without exposing an authority method. |
| 4 | `os.PathLike` boundaries preserve local sandbox semantics separately from portable serialized paths. | VERIFIED | The complete string, `Path`, custom PathLike, bytes, NUL, root, drive, dot, parent, backslash, Unicode, and component matrix passes. `LocalPath` and `PortablePath` are final distinct types and lexical normalization makes no symlink-containment claim. |
| 5 | Semantic failure categories are stable exceptions while legality remains normal typed data. | VERIFIED | Validation, concurrency, storage-integrity, transport, and capability-protocol exceptions expose stable safe codes. Accepted, rejected, deferred, and superseded outcomes remain frozen decision values; ports and fakes cannot mint legality or lifecycle Events. |

**Score:** 5/5 must-haves verified.

## Required Artifacts

| Artifact | Status | Verification |
|---|---|---|
| `src/openrund/contracts/` | VERIFIED | Complete immutable semantic inventory, exact Event catalog, decisions, and portable values; strict mypy passes. |
| `src/openrund/codec/` | VERIFIED | Bounded strict decode, exact encode, aliases, canonical JSON, hashes, and writer guards; golden corpus passes. |
| `src/openrund/ports/` | VERIFIED | Narrow domain-typed structural protocols with no authority implementation. |
| `src/openrund/_testing/` | VERIFIED | Private deterministic memory stores and seeded test substitutes; no package-root exposure. |
| `src/openrund/errors.py` and `src/openrund/paths.py` | VERIFIED | Safe semantic exception hierarchy and distinct local/portable path contracts. |
| `pyproject.toml`, `uv.lock`, and `src/openrund/py.typed` | VERIFIED | Reproducible Python 3.12 toolchain, strict gates, wheel/sdist, and installed typing marker. |
| `tests/codec/test_phase28_corpus.py` | VERIFIED | Exact authenticated category bijection, decision evidence, writer policy, round-trip/hash, and no-mutation checks. |
| `tests/package/test_import_hygiene.py` | VERIFIED | Dependency direction, codec confinement, minimal root, private fakes, and phase scope are machine enforced. |
| `tests/package/test_installed_typing.py` | VERIFIED | Isolated wheel import, strict installed consumer, `py.typed`, and complete public annotations pass. |

## Key-Link Verification

| Link | Status | Evidence |
|---|---|---|
| Authenticated manifest rows → semantic constructors and codecs | WIRED | Exact counts select 65 Events, four decisions, 18 wire cases, 14 numbers, six field-policy cases, and 19 rejections; every referenced file is authenticated before interpretation. |
| Semantic Event/decision values → exact v1 writers | WIRED | Explicit branch encoders reproduce all writer-eligible bytes, preserve required pointers, and fail closed for declaration-only superseded evidence. |
| Ports → deterministic substitutes | WIRED | Static conformance tests cover each store/runtime protocol while authority-surface tests reject lifecycle or legality methods. |
| Source package → built distribution | WIRED | Wheel/sdist build succeeds, wheel installs without source-tree access, `openrund` imports under `-I`, and a strict consumer resolves representative public types. |
| Phase scope → downstream phases | WIRED | Import hygiene forbids Views, storage, Engine, coordination, execution, providers, Bundle I/O, assembly, UI, and CLI implementation in the kernel. |

## Automated Evidence

| Check | Result |
|---|---|
| Exact documented Phase 28 gate | PASS |
| Full pytest suite | PASS — 415 passed |
| Strict mypy | PASS — 53 source files |
| Ruff lint and format | PASS |
| Lockfile validation | PASS |
| Wheel and source distribution | PASS |
| Installed-wheel strict consumer and isolated import | PASS |
| Plan completeness | PASS — 9 plans, 9 summaries |
| Final-plan artifact verification | PASS — 3/3 |
| Final-plan key-link verification | PASS — 3/3 |
| Schema drift | PASS — none detected |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| SEM-01 | SATISFIED | Canonical concepts and all Event/decision forms construct, validate, compare, freeze, encode, decode, and reject exactly. |
| DX-01 | SATISFIED | Idiomatic semantic names and explicit private wire aliases are mechanically separated. |
| DX-02 | SATISFIED | Final typed values, precise unions, complete annotations, strict mypy, and installed `py.typed` pass. |
| DX-03 | SATISFIED | Structural ports and deterministic private implementations pass behavior and typing contracts. |
| DX-05 | SATISFIED | Complete PathLike acceptance/rejection and local/portable path separation pass. |
| DX-08 | SATISFIED | Stable safe exception categories coexist with normal typed legality decisions. |

## Anti-Patterns and Human Verification

- No human-only verification is required; all five success criteria are machine-testable and passed.
- The final import-hygiene gate forbids graphical UI, UI-SPEC work, and CLI implementation in this phase.
- The codebase-drift tool emitted its expected advisory because no current mapper baseline exists and its inventory still describes the frozen source tree. It requested no mapper spawn, detected no schema drift, and does not weaken the phase-specific artifact, import, typing, corpus, or test evidence.
- No overrides were applied.

## Gaps

None.
