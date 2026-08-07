# Phase 31: Engine Authority and Core Run Semantics — Patterns

## Closest Existing Analogs

| New responsibility | Existing Python analog | Pattern to preserve |
|---|---|---|
| Engine dependency value | `src/openrund/ports/runtime.py` | Frozen, typed dependency assembly with one protocol per side effect |
| Authoritative history load | `src/openrund/views/_rebuild.py` | Complete contiguous replay at a declared watermark; incomplete history fails closed |
| Atomic decision commit | `src/openrund/storage/_events.py` and `src/openrund/ports/events.py` | Expected-position append with one ordered immutable batch |
| Event construction | `src/openrund/codec/_events.py` and Event payload classes | Explicit exhaustive branch mapping; no reflection or generic dataclass dumping |
| Legality evidence | `src/openrund/contracts/commands.py` | Immutable typed decisions and criterion-by-criterion trace entries |
| Run completion blockers | `src/openrund/views/_run_status.py` | Views explain blockers; only Engine turns those facts into a decision |
| Untrusted provider seam | `src/openrund/ports/providers.py` | Providers return proposals, never Events or authority decisions |
| Deterministic test dependencies | `src/openrund/_testing/` | Inject clock/IDs/stores and expose immutable observations |

## Dependency Direction

```text
contracts + ports + codec + views
              ↑
            engine
              ↑
     later assembly / CLI / loops
```

The Engine may depend on contracts, ports, codec helpers, and deterministic Views. Contracts, ports, codecs, Views, and storage adapters must not import the Engine. Provider and capability adapters remain unable to append lifecycle Events.

## Proposed File Map

| Path | Responsibility |
|---|---|
| `src/openrund/engine/__init__.py` | Small intentional Engine API |
| `src/openrund/engine/_model.py` | Engine dependencies, bootstrap input, and stable result values |
| `src/openrund/engine/_legality.py` | Pure, deterministic hard-invariant evaluation |
| `src/openrund/engine/_records.py` | Decision records, canonical content hashes, and `command.recorded` payloads |
| `src/openrund/engine/_events.py` | Explicit operation-to-lifecycle Event materialization |
| `src/openrund/engine/_engine.py` | Complete replay, evaluate, atomic append, conflict retry, and idempotent recovery |
| `src/openrund/engine/_proposals.py` | Model proposal adaptation without authority leakage |
| `tests/engine/` | Contract, legality, lifecycle, proposal, replay, and concurrency gates |

## Required Patterns

- Every attempted mutation has a caller-supplied or injected stable `CommandId` before evaluation.
- One append batch begins with exactly one `command.recorded`; accepted target Events follow and carry the same `command_id` in their envelopes.
- Rejected, deferred, and superseded decisions append no target lifecycle Events.
- A retry after an expected-position conflict re-reads complete history and re-evaluates; it never reuses a stale View.
- A repeated `CommandId` returns the already committed decision without another append.
- The Engine builds wire-compatible content through explicit codec helpers, never by importing private aliases into domain code.
- Convenience methods create Commands and delegate to `submit`; they are not alternate legality paths.

## Prohibited Patterns

- Public `append`, `emit`, or storage exposure on the Engine.
- EventStore access from providers, workers, proposal adapters, lifecycle helpers, or CLI code.
- Treating `RunCompletionReadiness.ready` as authority outside Engine legality evaluation.
- Trusting a provider response because it parsed successfully.
- Catching semantic rejection as provider/transport failure or converting transport failure into a rejected model Command.
- Generic dataclass/`__dict__` serialization, mutable dictionaries as authoritative state, or module globals for IDs/time.
- UI specifications, UI workflow gates, or graphical interaction artifacts.

## Test Map

- `test_contracts.py`: Engine inputs, runtime operations, dependency and validation rules.
- `test_records.py`: exact accepted/rejected/deferred/superseded command evidence and content hashes.
- `test_legality.py`: uncreated/running/terminal matrices and exhaustive completion blockers.
- `test_engine.py`: one path, one atomic batch, no target on denial, complete-history requirement.
- `test_concurrency.py`: stale writers, retry, duplicate Command IDs, idempotency supersession.
- `test_run_lifecycle.py`: bootstrap/start/complete/fail/cancel and terminal immutability.
- `test_model_lifecycle.py`: Message/ModelCall sequencing and failure classifications.
- `test_proposals.py`: provider output remains untrusted and legality is a separate outcome.
- `test_compatibility.py`: frozen `command.recorded` and lifecycle Event bytes.
- `test_hygiene.py`: no public append/storage authority and installed typing.
