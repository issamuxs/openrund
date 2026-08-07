# Phase 36 Patterns

## Closest Python Analogs

| New surface | Existing analog | Reuse |
|---|---|---|
| Local assembly | `EngineDependencies`, SQLite adapters, `ActionRunnerDependencies`, `DurableRunLoopDependencies` | Explicit typed construction and context-managed lifetime |
| CLI mutation | Engine convenience in tests | Construct one typed `Command` and submit through `RuntimeEngine` |
| CLI inspection | `rebuild_views` and Bundle replay/rendering | Exact watermark replay and immutable result values |
| CLI rendering | Bundle deterministic renderers | Stable ordered fields and canonical JSON |
| Demonstration | Capability integration tests | Seeded entropy, local-only workers, explicit governance, no network |

## Design Rules

- Production time and identity factories are injectable and prefix-kind-safe.
- Assembly owns only resources it constructs and closes them in reverse order.
- Read-only operator services depend on ports, not concrete SQLite implementations.
- Mutating operator methods accept explicit IDs and submit normal Commands.
- CLI parsing, execution, rendering, and process exit are separate functions.
- Package-root exports are allowlisted mechanically.
