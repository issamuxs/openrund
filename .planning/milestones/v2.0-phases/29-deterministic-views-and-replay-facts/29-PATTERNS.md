---
phase: 29-deterministic-views-and-replay-facts
status: complete
created: 2026-08-05
---

# Phase 29 Existing Patterns

## Closest Analogs

| New area | Closest existing pattern | Apply |
|---|---|---|
| `views/_model.py` | `contracts/*.py` | Final frozen, slotted, keyword-only dataclasses; constructor-time runtime validation; precise unions and typed IDs. |
| `views/_history.py` | `codec/_json.py` boundary validation | Validate the complete outer shape before constructing trusted replay input; safe stable issue codes; no partial trusted bundle. |
| Focused reducers | `codec/_events.py` explicit association dispatch | Exhaustive explicit Event-class dispatch; no reflection, `asdict`, generic model dumping, or wire aliases in semantic code. |
| Immutable keyed Views | `contracts/json.py` and `_testing/memory.py` | Preserve insertion order, copy mutable inputs, expose immutable tuples/mappings, and never leak internal mutation. |
| Corpus harness | `tests/conftest.py`, `test_phase28_corpus.py` | Verify containment, regular file, byte length, and SHA-256 before decoding; exact category counts and before/after tree snapshot. |
| Reducer conformance tests | `tests/contracts/test_event_catalog.py` | Table-driven exact branch coverage plus strict typing and runtime rejection tests. |

## Dependency Direction

```text
contracts + errors
       ↓
     views
       ↓
codec test projection / later bundles / later engine
```

`views` may import semantic contracts and semantic errors. It must not import ports, storage, engine, capabilities, providers, bundles, CLI, test fakes, or raw frozen-corpus loaders.

## Naming and API Shape

- Semantic names use `snake_case`.
- Canonical ontology types remain in `openrund.contracts`; derived types use suffixes such as `View`, `Receipt`, `Report`, `Entry`, `Replay`, and `Issue`.
- Public reducer entry points accept already-decoded `RuntimeEvent` values.
- `rebuild_views(...)` returns a precise `CompleteViewReplay | IncompleteViewReplay` union.
- Focused reducers remain importable from `openrund.views`, but `openrund.__init__` remains unexpanded.

## Prohibited Patterns

- No mutable dictionaries/lists in returned public state.
- No sorting by hash, set iteration, wall clock, random ID, process state, cache state, or filesystem traversal.
- No `Protocol` method that appends Events or asks storage for an undeclared watermark.
- No bool flag such as `assume_complete=True` that bypasses history validation.
- No UI or CLI rendering in reducer modules.
