---
phase: 28
slug: python-contract-kernel
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest on Python 3.12+; mypy strict typing; Ruff lint/format |
| **Config file** | Root `pyproject.toml` — Wave 0 creates the Python project and test/tool configuration |
| **Quick run command** | `uv run --python 3.12 pytest tests/contracts tests/ports -q` |
| **Full suite command** | `uv run --python 3.12 pytest -q && uv run --python 3.12 mypy --strict src/openrund tests && uv run ruff check src tests && uv run ruff format --check src tests` |
| **Estimated runtime** | ~60 seconds before the complete corpus matrix; ~180 seconds at phase completion |

---

## Sampling Rate

- **After every task commit:** Run the narrowest named pytest file plus mypy on the changed module.
- **After every plan wave:** Run `uv run --python 3.12 pytest -q` and the strict mypy/Ruff gates.
- **Before phase verification:** Run the full suite, build wheel/sdist, inspect `py.typed`, and execute the complete Phase 28 frozen-corpus matrix.
- **Max feedback latency:** 60 seconds for focused tests; 180 seconds for the final corpus/package gate.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | DX-02 | T-28-01-PKG | The Python 3.12+ root package, locked development toolchain, wheel/sdist metadata, minimal root, and `py.typed` marker are reproducible. | package/tooling | `uv lock --check && uv build && uv run --python 3.12 pytest tests/package/test_py_typed.py -q` | ✅ W1 | ✅ green |
| 28-01-02 | 01 | 1 | DX-01, DX-02 | T-28-01-CORPUS | Corpus helpers reject escaping/symlink/non-regular entries and verify byte length plus SHA-256 before returning inert evidence. | fixture/security | `uv run --python 3.12 pytest tests/package/test_fixture_integrity.py -q` | ✅ W1 | ✅ green |
| 28-02-01 | 02 | 2 | SEM-01, DX-02, DX-08 | T-28-02-TYPE | Stable safe exceptions and every kind-safe ID reject empty, `None`, booleans, and wrong runtime kinds without unsafe detail. | unit/TDD | `uv run --python 3.12 pytest tests/contracts/test_ids.py tests/contracts/test_errors.py -q` | ✅ W2 | ✅ green |
| 28-02-02 | 02 | 2 | SEM-01, DX-02 | T-28-02-VALUE | Deeply immutable ordered JSON, missing/null/value presence, exact UTF-8 equality, and canonical timestamps are runtime validated. | unit/TDD | `uv run --python 3.12 pytest tests/contracts/test_values.py -q` | ✅ W2 | ✅ green |
| 28-02-03 | 02 | 2 | DX-05 | T-28-02-PATH | `str`, `Path`, and custom string PathLike inputs normalize distinctly from portable paths; bytes, NUL, roots, drives, dot/parent segments, and backslashes reject. | unit/TDD | `uv run --python 3.12 pytest tests/contracts/test_paths.py -q` | ✅ W2 | ✅ green |
| 28-03-01 | 03 | 3 | SEM-01, DX-02 | T-28-03-VALUE, T-28-03-UTF8 | Canonical leaf concepts are frozen/deeply immutable/annotated; Content equality and UTF-8 byte length preserve empty/ASCII/BMP/astral/composed/decomposed code points without normalization. | contract/TDD | `uv run --python 3.12 pytest tests/contracts/test_leaf_concepts.py -q` | ✅ W3 | ✅ green |
| 28-03-02 | 03 | 3 | SEM-01, DX-02, DX-08 | T-28-03-AUTH, T-28-03-RECORD | Runtime decisions remain strict normal values; lossless standalone CommandDecisionRecord branches preserve every fixture field/pointer without fabricated reasons. | contract/TDD | `uv run --python 3.12 pytest tests/contracts/test_concepts.py tests/contracts/test_commands.py -q` | ✅ W3 | ✅ green |
| 28-04-01 | 04 | 4 | SEM-01, DX-01, DX-02 | T-28-04-CATALOG | All 37 Event names and 65 frozen payload variants have exact type/version/payload associations, with legacy read forms distinct from canonical writer forms. | contract/TDD | `uv run --python 3.12 pytest tests/contracts/test_event_catalog.py -q` | ✅ W4 | ✅ green |
| 28-05-01 | 05 | 5 | DX-01, DX-02, DX-08 | T-28-05-WIRE | Strict JSON/JSONL parsing rejects malformed UTF-8, framing drift, duplicate keys, unsafe/non-finite numbers, excessive bytes/depth/items, and type confusion before domain construction. | codec/security/TDD | `uv run --python 3.12 pytest tests/codec/test_json_decode.py -q` | ✅ W5 | ✅ green |
| 28-05-02 | 05 | 5 | SEM-01, DX-01, DX-02, DX-08 | T-28-05-EVENT, T-28-05-DECISION | Event decoding stays exact; `decode_command_decision` returns lossless records with all target/rejection/Wait/declaration pointers and shares only compatible fields with command.recorded. | codec/golden/TDD | `uv run --python 3.12 pytest tests/codec/test_v1_decode.py tests/codec/test_rejections.py -q` | ✅ W5 | ✅ green |
| 28-06-01 | 06 | 6 | SEM-01, DX-01 | T-28-06-ENCODE, T-28-06-DECISION | Event encoding stays exact; accepted/rejected/deferred records round-trip all pointers/bytes without reasons, while superseded is decode-only and applicable writers reject it. | codec/golden/TDD | `uv run --python 3.12 pytest tests/codec/test_v1_encode.py tests/codec/test_v1_events.py -q` | ✅ W6 | ✅ green |
| 28-06-02 | 06 | 6 | SEM-01, DX-01 | T-28-06-HASH | Canonical JSON recursively orders keys by documented UTF-16 code-unit order without Unicode normalization and matches every scoped semantic preimage/hash. | codec/golden/TDD | `uv run --python 3.12 pytest tests/codec/test_canonical_json.py -q` | ✅ W6 | ✅ green |
| 28-07-01 | 07 | 5 | DX-03, DX-08 | T-28-07-PORT | Event, Artifact, and Lease store protocols are narrow, domain-typed structural contracts with no concrete persistence or legality behavior. | contract/type/TDD | `uv run --python 3.12 pytest tests/ports/test_store_protocols.py -q && uv run --python 3.12 mypy --strict src/openrund/ports tests/ports/test_store_protocols.py` | ✅ W5 | ✅ green |
| 28-07-02 | 07 | 5 | DX-03, DX-08 | T-28-07-PORT | Clock, generic ID factory, provider, capability transport, and reporter protocols type-check structurally without runtime-checkable weakening. | contract/type/TDD | `uv run --python 3.12 pytest tests/ports/test_runtime_protocols.py -q && uv run --python 3.12 mypy --strict src/openrund/ports tests/ports/test_runtime_protocols.py` | ✅ W5 | ✅ green |
| 28-08-01 | 08 | 6 | DX-03, DX-08 | T-28-08-FAKE | Private in-memory contract stores preserve insertion order, freeze inputs, return domain values, and expose deterministic calls without durability claims. | contract/TDD | `uv run --python 3.12 pytest tests/ports/test_memory_stores.py -q` | ✅ W6 | ✅ green |
| 28-08-02 | 08 | 6 | DX-03, DX-08 | T-28-08-FAKE | Seeded clock/ID/provider/transport/reporter fakes have immutable ordered logs, deterministic exhaustion, and no authority or Event-fabrication path. | contract/TDD | `uv run --python 3.12 pytest tests/ports/test_deterministic_fakes.py -q` | ✅ W6 | ✅ green |
| 28-09-01 | 09 | 7 | SEM-01, DX-01, DX-02, DX-03, DX-05, DX-08 | T-28-09-MATRIX, T-28-09-DECISION | The scoped matrix proves 65 Events, four lossless CommandDecisionRecord mappings with every required pointer/no invented reasons/compatible helper reuse/superseded writer prohibition, Content UTF-8 vectors, 18 encoding, 14 number, six field-policy, and relevant rejections. | integration/security | `uv run --python 3.12 pytest tests/codec/test_phase28_corpus.py tests/package/test_import_hygiene.py tests/contracts/test_leaf_concepts.py -q` | ✅ W7 | ✅ green |
| 28-09-02 | 09 | 7 | SEM-01, DX-01, DX-02, DX-03, DX-05, DX-08 | T-28-09-RELEASE | Full pytest, strict mypy, Ruff, wheel/sdist, built-wheel typing/import, and frozen-corpus gates pass together. | integration/package | `uv run --python 3.12 pytest -q && uv run --python 3.12 mypy --strict src/openrund tests && uv run ruff check src tests && uv run ruff format --check src tests && uv lock --check && uv build` | ✅ W7 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The planner may regroup these rows into a different plan count, but it must preserve every behavior and update Task IDs/waves so each executable task has a matching automated row.

---

## Wave 0 Requirements

- [x] `pyproject.toml` — Python 3.12+ build metadata plus pytest, strict mypy, Ruff, and package-data configuration.
- [x] `src/openrund/__init__.py` and `src/openrund/py.typed` — package root and PEP 561 marker.
- [x] `tests/conftest.py` — read-only frozen-manifest/evidence fixtures with hash validation and Phase 28 category selection.
- [x] `tests/package/test_py_typed.py` — built-wheel marker and import checks.
- [x] A locked Python development dependency set usable through `uv run --python 3.12` without relying on the system Python 3.9 interpreter.

---

## Manual-Only Verifications

All Phase 28 success criteria are machine-testable. No manual-only verification is required.

---

## Corpus Contract

- Load `tests/fixtures/compatibility/v1/manifest.json` and referenced evidence read-only; verify each hash before interpreting the case.
- Exercise every Event, Command-decision, encoding, number, presence/field-policy, and relevant rejection entry owned by Phase 28.
- Do not invoke generator/verifier scripts as implementation dependencies and never rewrite the frozen corpus.
- Keep View reduction, concrete SQLite/Artifact custody, provider adapters, Bundle I/O, Engine authority, CLI behavior, and graphical UI outside this phase.

---

## Validation Sign-Off

- [x] Every prospective task has automated verification or an explicit Wave 0 dependency.
- [x] Sampling continuity has no three-task gap.
- [x] Wave 0 covers every currently missing Python test/tool artifact.
- [x] No watch-mode, snapshot-update, fixture-update, or corpus-generation flags are used.
- [x] Focused feedback latency target is below 60 seconds.
- [x] `nyquist_compliant: true` records complete requirement-to-test coverage; `wave_0_complete` stays false until execution creates and passes the files.

**Approval:** execution complete — 2026-08-05; exact full gate passed with 415 tests.
