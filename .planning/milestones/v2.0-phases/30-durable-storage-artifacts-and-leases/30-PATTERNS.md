---
phase: 30-durable-storage-artifacts-and-leases
status: complete
created: 2026-08-05
---

# Phase 30 Existing Patterns

## Closest Analogs

| New area | Closest Python pattern | Apply |
|---|---|---|
| `storage/_database.py` | `codec/_json.py` | One deep boundary validates external state, emits safe stable errors, and hides infrastructure details. |
| `storage/_events.py` | `codec/_events.py`, `ports/events.py` | Explicit Event encode/decode; typed inputs/results; exhaustive validation without reflection. |
| `storage/_artifacts.py` | `ports/artifacts.py`, `paths.py` | Frozen storage values, copied bytes/JSON, lexical validation followed by adapter-owned containment checks. |
| `storage/_leases.py` | `ports/leases.py`, `_testing/memory.py` | Deterministic injected time/ID/token sources and conditional domain results. |
| `storage/_layout.py` | `paths.py` | Pure lexical path construction separated from filesystem mutation. |
| SQLite compatibility harness | `tests/compatibility/test_phase28_corpus.py`, `tests/views/test_fixture_integrity.py` | Authenticate containment, byte length, and SHA-256 before copying evidence to a temporary directory. |
| Conformance/fault tests | `tests/ports/test_memory_stores.py`, `tests/views/test_view_determinism.py` | Table-driven boundary cases, fresh-instance/reopen checks, strict exception codes, and no hidden global state. |

## Proposed File Map

```text
src/openrund/
├── storage/
│   ├── __init__.py
│   ├── _database.py
│   ├── _events.py
│   ├── _artifacts.py
│   ├── _leases.py
│   ├── _event_log.py
│   └── _layout.py
├── ports/
│   ├── events.py
│   ├── artifacts.py
│   └── leases.py
├── contracts/runs.py
├── errors.py
├── paths.py
└── _testing/memory.py

tests/
├── storage/
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_events.py
│   ├── test_event_concurrency.py
│   ├── test_event_log.py
│   ├── test_artifacts.py
│   ├── test_artifact_recovery.py
│   ├── test_leases.py
│   ├── test_layout.py
│   ├── test_compatibility.py
│   └── test_hygiene.py
└── ports/
    ├── test_store_protocols.py
    └── test_memory_stores.py
```

## Dependency Direction

```text
contracts + errors + paths + codec
                 ↓
               ports
                 ↓
              storage
                 ↓
       later runtime assembly / engine
```

`storage` may implement ports and use public codecs. Contracts and ports must not import SQLite, filesystem custody, Engine, providers, capabilities, Bundles, CLI, or test substitutes. The Event log wrapper may notify observers only after the implemented store returns a committed result.

## Naming and API Shape

- Public Python names use `snake_case`; schema column names remain authenticated storage spellings.
- Adapters are `SqliteRunEventStore`, `SqliteArtifactStore`, and `SqliteExecutionLeaseStore` under `openrund.storage`.
- Public constructors accept `os.PathLike[str] | str` and validate them through the established local-path boundary.
- Configuration such as busy timeout is explicit, finite, validated, and immutable after construction.
- SQLite connections, rows, cursors, SQL exceptions, staging paths, and fault hooks are private implementation details.
- Fault injection is a private/test seam with named checkpoints; production callers cannot use it to bypass validation.

## Prohibited Patterns

- No connection or transaction survives an `await`.
- No shared global SQLite connection.
- No implicit transaction mode, infinite busy retry, or sleep loop.
- No overwrite-capable Artifact publication and no absolute `blob_path` persisted in SQLite.
- No following symlinks while scanning, publishing, recovering, or creating Run homes.
- No generic Event serialization, partial-history return, or silent gap repair.
- No owner-only Lease release after fencing tokens exist.
- No Lease or filesystem path treated as Authority.
- No CLI command, UI artifact, UI specification, or presentation rendering in this phase.
